from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.txt").write_text("hello file", encoding="utf-8")

        options = rightcode_options(cwd=root, project_dir=root, allowed_tools=["Read"])
        prompt = "Use the Read tool to read file 'a.txt'. Then reply with exactly: READ_OK:<file contents>."
        printer = ConsoleRenderer(debug=console_debug_enabled())
        await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
