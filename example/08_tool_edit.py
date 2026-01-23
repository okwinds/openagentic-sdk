from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options

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
        print(f"a.txt={ (root / 'a.txt').read_text(encoding='utf-8')!r }")


if __name__ == "__main__":
    asyncio.run(main())
