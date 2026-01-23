from __future__ import annotations

import asyncio

from _common import example_artifact_dir, repo_root, require_env_simple, rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    require_env_simple(
        "TAVILY_API_KEY",
        help="This example uses the WebSearch tool (Tavily). Set TAVILY_API_KEY then rerun.",
    )

    out_dir = example_artifact_dir("22")
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
    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt=prompt, options=options, renderer=printer)

    if report_path.exists():
        print(f"Wrote: {report_path}")
    else:
        print(f"Expected report at: {report_path} (but it was not created)")


if __name__ == "__main__":
    asyncio.run(main())
