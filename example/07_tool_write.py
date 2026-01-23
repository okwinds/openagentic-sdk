from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        options = rightcode_options(cwd=root, project_dir=root, allowed_tools=["Write", "Read"])
        prompt = (
            "Use the Write tool to create 'out.txt' with content exactly 'hello write'. "
            "Then use the Read tool to read it back. "
            "Finally reply with exactly: WRITE_OK:<file contents>."
        )
        debug = console_debug_enabled()
        printer = ConsoleRenderer(debug=debug)
        await console_query(prompt=prompt, options=options, renderer=printer)
        if (root / "out.txt").exists():
            if debug:
                print(f"out.txt={ (root / 'out.txt').read_text(encoding='utf-8')!r }")


if __name__ == "__main__":
    asyncio.run(main())
