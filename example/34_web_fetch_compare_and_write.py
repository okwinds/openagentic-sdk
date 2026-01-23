from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        options = rightcode_options(
            cwd=root,
            project_dir=root,
            allowed_tools=["WebFetch", "Write"],
            permission_mode="bypass",
            interactive=False,
        )
        prompt = (
            "Compare two pages.\n"
            "1) Use WebFetch url='https://example.com' prompt='Summarize in 1 sentence'.\n"
            "2) Use WebFetch url='https://www.iana.org/domains/example' prompt='Summarize in 1 sentence'.\n"
            "3) Use Write to create compare.md with both summaries and a short comparison.\n"
            "Finally reply with COMPARE_OK."
        )
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)

        if (root / "compare.md").exists():
            print(f"Wrote: {root / 'compare.md'}")


if __name__ == "__main__":
    asyncio.run(main())

