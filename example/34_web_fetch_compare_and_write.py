from __future__ import annotations

import asyncio
from pathlib import Path

from _common import example_artifact_dir, repo_root, rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled

from open_agent_sdk import query


async def main() -> None:
    out_dir = example_artifact_dir("34")
    options = rightcode_options(
        cwd=out_dir,
        project_dir=repo_root(),
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
    printer = ConsoleRenderer(debug=console_debug_enabled())
    async for ev in query(prompt=prompt, options=options):
        printer.on_event(ev)

    out_path = out_dir / "compare.md"
    if out_path.exists():
        print(f"Wrote: {out_path}")
    else:
        print(f"Expected comparison at: {out_path} (but it was not created)")


if __name__ == "__main__":
    asyncio.run(main())
