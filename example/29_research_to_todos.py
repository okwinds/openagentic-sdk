from __future__ import annotations

import asyncio

from _common import EventPrinter, example_debug_enabled, repo_root, require_env_simple, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    require_env_simple(
        "TAVILY_API_KEY",
        help="This example uses the WebSearch tool (Tavily). Set TAVILY_API_KEY then rerun.",
    )

    options = rightcode_options(
        cwd=repo_root(),
        project_dir=repo_root(),
        allowed_tools=["WebSearch", "TodoWrite"],
        permission_mode="bypass",
        interactive=False,
    )
    prompt = (
        "Research then plan.\n"
        "1) Use WebSearch query='python asyncio best practices' max_results=5.\n"
        "2) Based on results, create a 6-item learning plan as TODOs and call TodoWrite.\n"
        "Finally reply with RESEARCH_TODO_OK."
    )
    printer = EventPrinter(debug=example_debug_enabled())
    async for ev in query(prompt=prompt, options=options):
        printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())

