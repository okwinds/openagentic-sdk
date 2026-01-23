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
        (root / ".claude" / "commands").mkdir(parents=True)
        (root / ".claude" / "commands" / "hello.md").write_text("Hello from /hello", encoding="utf-8")

        options = rightcode_options(cwd=root, project_dir=root, allowed_tools=["SlashCommand"])
        prompt = (
            "Call the SlashCommand tool with name='hello' to load `.claude/commands/hello.md`. "
            "Then reply with exactly: SLASH_OK:<the loaded content>."
        )
        printer = ConsoleRenderer(debug=console_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())
