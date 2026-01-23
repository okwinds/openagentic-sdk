from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any, AsyncIterable, AsyncIterator

from .message_query import query_messages
from .messages import Message, ResultMessage
from .options import OpenAgentOptions
from .prompting import coerce_prompt
from .sessions.store import FileSessionStore


def _default_session_root() -> Path:
    env = os.environ.get("OPEN_AGENT_SDK_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".open-agent-sdk"


class OpenAgentSDKClient:
    def __init__(self, options: OpenAgentOptions | None = None) -> None:
        self._base_options = options
        self._store: FileSessionStore | None = None
        self._session_id: str | None = None

        self._queue: asyncio.Queue[Message | None] | None = None
        self._runner: asyncio.Task[None] | None = None
        self._abort_event: asyncio.Event | None = None

    async def __aenter__(self) -> "OpenAgentSDKClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.disconnect()

    async def connect(self, prompt: str | AsyncIterable[dict[str, Any]] | None = None) -> None:
        if self._base_options is None:
            raise ValueError("OpenAgentSDKClient: options is required")

        if self._store is None:
            store = self._base_options.session_store
            if store is None:
                root = self._base_options.session_root or _default_session_root()
                store = FileSessionStore(root_dir=root)
            self._store = store

        if self._session_id is None:
            if self._base_options.resume:
                self._session_id = self._base_options.resume
            else:
                # Create a durable session id + meta.json.
                self._session_id = self._store.create_session(metadata={"cwd": self._base_options.cwd})

        if prompt is not None:
            await self.query(prompt)

    async def query(self, prompt: str | AsyncIterable[dict[str, Any]], session_id: str = "default") -> None:
        if self._base_options is None:
            raise ValueError("OpenAgentSDKClient: options is required")
        if self._store is None:
            await self.connect()

        if self._session_id is None:
            if session_id and session_id != "default":
                self._session_id = session_id
            else:
                self._session_id = uuid.uuid4().hex

        if self._runner is not None:
            raise RuntimeError("OpenAgentSDKClient: a query is already in progress")

        q: asyncio.Queue[Message | None] = asyncio.Queue()
        self._queue = q
        abort_event = asyncio.Event()
        self._abort_event = abort_event

        run_options = replace(self._base_options, session_store=self._store, resume=self._session_id, abort_event=abort_event)

        async def _run() -> None:
            try:
                prompt_text = await coerce_prompt(prompt)
                async for m in query_messages(prompt=prompt_text, options=run_options):
                    await q.put(m)
            finally:
                self._abort_event = None
                await q.put(None)

        self._runner = asyncio.create_task(_run())

    async def receive_messages(self) -> AsyncIterator[Message]:
        q = self._queue
        if q is None:
            return
        while True:
            m = await q.get()
            if m is None:
                break
            yield m

        if self._runner is not None:
            await self._runner
        self._runner = None
        self._queue = None

    async def receive_response(self) -> AsyncIterator[Message]:
        q = self._queue
        if q is None:
            return

        seen_result = False
        while True:
            m = await q.get()
            if m is None:
                break
            if not seen_result:
                yield m
            if isinstance(m, ResultMessage):
                seen_result = True

        if self._runner is not None:
            await self._runner
        self._runner = None
        self._queue = None

    async def interrupt(self) -> None:
        if self._abort_event is not None:
            self._abort_event.set()

    async def disconnect(self) -> None:
        if self._runner is not None:
            await self._runner
        self._runner = None
        self._queue = None
        # Keep session id for continuity unless caller discards the client.
