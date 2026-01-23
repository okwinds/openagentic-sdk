from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "README.md").write_text(
            "# Demo Project\n\nThis project uses MCP and Skills.\n\n## MCP\nMCP is planned.\n\n## Skills\nUse skills.\n",
            encoding="utf-8",
        )

        options = rightcode_options(
            cwd=root,
            project_dir=root,
            allowed_tools=["Read", "Grep", "Write", "TodoWrite"],
            permission_mode="bypass",
            interactive=False,
        )
        prompt = (
            "Onboard to the project.\n"
            "1) Use Read to read README.md.\n"
            "2) Use Grep (query='MCP') to find where MCP is discussed.\n"
            "3) Use Write to create ONBOARDING.md with a short summary + links to key sections.\n"
            "4) Use TodoWrite to create 4 TODOs for next steps.\n"
            "Finally reply with ONBOARDING_NOTES_OK."
        )
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)

        if (root / "ONBOARDING.md").exists():
            print(f"Wrote: {root / 'ONBOARDING.md'}")


if __name__ == "__main__":
    asyncio.run(main())

