import asyncio
import os
import sys

sys.dont_write_bytecode = True

from _common import repo_root, rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    _ = os.environ  # used implicitly by rightcode_options()
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=["Read", "Edit", "Bash"])

    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt="Find and fix the bug in auth.py", options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
