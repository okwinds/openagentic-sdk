from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "note.txt").write_text("hello", encoding="utf-8")

        # Only allow Read, so any attempt to use other tools will be denied by the runtime.
        options = rightcode_options(
            cwd=root,
            project_dir=root,
            allowed_tools=["Read"],
            permission_mode="bypass",
            interactive=False,
        )
        prompt = (
            "Try to run Bash `echo hi` (even if it's not allowed). If it's denied, acknowledge the denial.\n"
            "Then use Read to read note.txt and reply with SANDBOX_OK."
        )
        debug = console_debug_enabled()
        printer = ConsoleRenderer(debug=debug)
        if not debug:
            print("Tip: run with --debug to see tool denial details.")
        await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
