from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        options = rightcode_options(cwd=root, project_dir=root, allowed_tools=["Bash"])
        prompt = "Use the Bash tool to run `echo hello bash`. Then reply with exactly: BASH_OK:<stdout>."
        printer = ConsoleRenderer(debug=console_debug_enabled())
        await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
