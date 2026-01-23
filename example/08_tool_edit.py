from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled

from open_agent_sdk import query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.txt").write_text("hello world", encoding="utf-8")

        options = rightcode_options(cwd=root, project_dir=root, allowed_tools=["Edit", "Read"])
        prompt = (
            "Use the Edit tool to replace 'world' with 'there' in file 'a.txt' (replace only once). "
            "Then use Read to read the file. "
            "Finally reply with exactly: EDIT_OK:<file contents>."
        )
        debug = console_debug_enabled()
        printer = ConsoleRenderer(debug=debug)
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)
        if debug:
            print(f"a.txt={ (root / 'a.txt').read_text(encoding='utf-8')!r }")


if __name__ == "__main__":
    asyncio.run(main())
