from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        options = rightcode_options(cwd=root, project_dir=root, allowed_tools=["Write", "Read"])
        prompt = (
            "Use the Write tool to create 'out.txt' with content exactly 'hello write'. "
            "Then use the Read tool to read it back. "
            "Finally reply with exactly: WRITE_OK:<file contents>."
        )
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)
        if (root / "out.txt").exists():
            if example_debug_enabled():
                print(f"out.txt={ (root / 'out.txt').read_text(encoding='utf-8')!r }")


if __name__ == "__main__":
    asyncio.run(main())
