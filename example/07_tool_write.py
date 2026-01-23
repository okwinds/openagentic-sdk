from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options

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
        if (root / "out.txt").exists():
            print(f"out.txt={ (root / 'out.txt').read_text(encoding='utf-8')!r }")


if __name__ == "__main__":
    asyncio.run(main())
