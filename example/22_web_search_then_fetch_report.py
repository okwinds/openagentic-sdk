from __future__ import annotations

import asyncio
from pathlib import Path

from _common import EventPrinter, example_debug_enabled, repo_root, require_env_simple, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    require_env_simple(
        "TAVILY_API_KEY",
        help="This example uses the WebSearch tool (Tavily). Set TAVILY_API_KEY then rerun.",
    )

    out_dir = repo_root() / ".open-agent-sdk" / "example-artifacts" / "22"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.md"

    options = rightcode_options(
        cwd=out_dir,
        project_dir=repo_root(),
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

    if report_path.exists():
        print(f"Wrote: {report_path}")
    else:
        print(f"Expected report at: {report_path} (but it was not created)")


if __name__ == "__main__":
    asyncio.run(main())
