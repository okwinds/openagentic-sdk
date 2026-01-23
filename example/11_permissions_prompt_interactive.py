from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        print("This example will prompt once: Allow tool Write? [y/N]")

        options = rightcode_options(cwd=root, project_dir=root, allowed_tools=["Write"])
        prompt = "Use the Write tool to create out.txt with content 'hello approvals'. Then reply with PERM_OK."

        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())
