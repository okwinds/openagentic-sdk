from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.txt").write_text("hello a", encoding="utf-8")
        (root / "b.txt").write_text("nope", encoding="utf-8")
        (root / "sub").mkdir()
        (root / "sub" / "c.txt").write_text("hello c", encoding="utf-8")

        options = rightcode_options(cwd=root, project_dir=root, allowed_tools=["Glob", "Grep"])
        prompt = (
            "Use Glob with root '.' and pattern '**/*.txt', then use Grep with query 'hello' and root '.'. "
            "Finally reply with: GLOB_GREP_OK and include the total match count."
        )
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())
