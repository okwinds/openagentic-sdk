from __future__ import annotations

import asyncio
from dataclasses import replace

from _common import repo_root, rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled

from open_agent_sdk import query_messages
from open_agent_sdk.messages import ResultMessage, StreamEvent


async def main() -> None:
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    options = replace(options, include_partial_messages=True)
    renderer = ConsoleRenderer(debug=console_debug_enabled())

    async for m in query_messages(prompt="Write a short sentence. Include token QUERY_MESSAGES_OK.", options=options):
        renderer.on_message(m)
        if isinstance(m, ResultMessage) and renderer.debug:
            print(f"[debug] subtype={m.subtype} session_id={m.session_id}")


if __name__ == "__main__":
    asyncio.run(main())
