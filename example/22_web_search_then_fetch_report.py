from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, require_env_simple, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    require_env_simple(
        "TAVILY_API_KEY",
        help="This example uses the WebSearch tool (Tavily). Set TAVILY_API_KEY then rerun.",
    )

    with TemporaryDirectory() as td:
        root = Path(td)
        options = rightcode_options(
            cwd=root,
            project_dir=root,
            allowed_tools=["WebSearch", "WebFetch", "Write"],
            permission_mode="bypass",
            interactive=False,
        )
        prompt = (
            "You are preparing a short research report.\n"
            "1) Use WebSearch with query='OpenAI API rate limits' and max_results=3.\n"
            "2) Pick the most relevant result URL and use WebFetch on it with prompt='Extract 5 key points'.\n"
            "3) Use Write to create report.md containing: the query, the chosen URL, and the 5 key points.\n"
            "Finally reply with REPORT_OK and mention report.md was written."
        )
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)

        if example_debug_enabled() and (root / "report.md").exists():
            print(f"[debug] report_path={root / 'report.md'}")


if __name__ == "__main__":
    asyncio.run(main())

