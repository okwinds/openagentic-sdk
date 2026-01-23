from __future__ import annotations

import asyncio

from _common import EventPrinter, example_debug_enabled, repo_root, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    printer = EventPrinter(debug=example_debug_enabled())
    async for ev in query(prompt="Write a short sentence about streaming. Include token STREAM_OK.", options=options):
        printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())
