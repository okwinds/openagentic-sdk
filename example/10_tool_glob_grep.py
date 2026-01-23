from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


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
        printer = ConsoleRenderer(debug=console_debug_enabled())
        await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
