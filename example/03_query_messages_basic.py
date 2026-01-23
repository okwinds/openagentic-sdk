from __future__ import annotations

import asyncio
from dataclasses import replace

from _common import repo_root, rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled, console_query_messages


async def main() -> None:
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    options = replace(options, include_partial_messages=True)
    renderer = ConsoleRenderer(debug=console_debug_enabled())

    await console_query_messages(prompt="Write a short sentence. Include token QUERY_MESSAGES_OK.", options=options, renderer=renderer)


if __name__ == "__main__":
    asyncio.run(main())
