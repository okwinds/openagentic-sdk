from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt="Write a short sentence about streaming. Include token STREAM_OK.", options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
