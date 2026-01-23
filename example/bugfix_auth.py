import asyncio
import os
import sys

sys.dont_write_bytecode = True

from _common import EventPrinter, example_debug_enabled, repo_root, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    _ = os.environ  # used implicitly by rightcode_options()
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=["Read", "Edit", "Bash"])

    printer = EventPrinter(debug=example_debug_enabled())
    async for event in query(prompt="Find and fix the bug in auth.py", options=options):
        printer.on_event(event)


if __name__ == "__main__":
    asyncio.run(main())
