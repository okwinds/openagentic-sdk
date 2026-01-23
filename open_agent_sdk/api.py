from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Sequence

from .options import OpenAgentOptions
from .runtime import AgentRuntime, RunResult


async def query(*, prompt: str, options: OpenAgentOptions) -> AsyncIterator[Any]:
    runtime = AgentRuntime(options)
    async for e in runtime.query(prompt):
        yield e


async def run(*, prompt: str, options: OpenAgentOptions) -> RunResult:
    events: list[Any] = []
    final_text = ""
    session_id = options.resume or ""
    async for e in query(prompt=prompt, options=options):
        events.append(e)
        if getattr(e, "type", None) == "system.init":
            session_id = getattr(e, "session_id", session_id)
        if getattr(e, "type", None) == "result":
            final_text = getattr(e, "final_text", "")
    return RunResult(final_text=final_text, session_id=session_id, events=events)

