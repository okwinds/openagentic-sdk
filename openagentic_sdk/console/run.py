from __future__ import annotations

from typing import Any

from ..api import query, query_messages, run
from ..client import OpenAgentSDKClient
from ..messages import ResultMessage
from ..options import OpenAgentOptions
from .renderer import ConsoleRenderer, console_debug_enabled


async def console_run(
    *,
    prompt: str,
    options: OpenAgentOptions,
    debug: bool | None = None,
) -> Any:
    dbg = console_debug_enabled() if debug is None else bool(debug)
    try:
        return await run(prompt=prompt, options=options)
    except Exception as e:  # noqa: BLE001
        if dbg:
            raise
        raise SystemExit(str(e).strip() or "Request failed") from None


async def console_query(
    *,
    prompt: str,
    options: OpenAgentOptions,
    renderer: ConsoleRenderer | None = None,
) -> None:
    r = renderer or ConsoleRenderer(debug=console_debug_enabled())
    try:
        async for ev in query(prompt=prompt, options=options):
            r.on_event(ev)
    except Exception as e:  # noqa: BLE001
        if r.debug:
            raise
        raise SystemExit(str(e).strip() or "Request failed") from None


async def console_query_messages(
    *,
    prompt: str,
    options: OpenAgentOptions,
    renderer: ConsoleRenderer | None = None,
) -> None:
    r = renderer or ConsoleRenderer(debug=console_debug_enabled())
    try:
        async for msg in query_messages(prompt=prompt, options=options):
            r.on_message(msg)
    except Exception as e:  # noqa: BLE001
        if r.debug:
            raise
        raise SystemExit(str(e).strip() or "Request failed") from None


async def console_client_turn(
    *,
    client: OpenAgentSDKClient,
    prompt: str,
    renderer: ConsoleRenderer | None = None,
) -> ResultMessage | None:
    r = renderer or ConsoleRenderer(debug=console_debug_enabled())
    try:
        await client.query(prompt)
        last_result: ResultMessage | None = None
        async for msg in client.receive_response():
            r.on_message(msg)
            if isinstance(msg, ResultMessage):
                last_result = msg
        return last_result
    except Exception as e:  # noqa: BLE001
        if r.debug:
            raise
        raise SystemExit(str(e).strip() or "Request failed") from None
