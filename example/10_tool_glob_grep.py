from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options

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
        async for ev in query(prompt=prompt, options=options):
            if ev.type == "assistant.delta":
                print(ev.text_delta, end="", flush=True)
            elif ev.type == "assistant.message":
                print()
                print(ev.text)
            elif ev.type == "tool.use":
                print(f"\n[tool.use] {ev.name} {ev.input}")
            elif ev.type == "tool.result":
                print(f"[tool.result] error={ev.is_error} output={ev.output}")
            elif ev.type == "result":
                print(f"[result] session_id={ev.session_id} stop_reason={ev.stop_reason}")


if __name__ == "__main__":
    asyncio.run(main())
