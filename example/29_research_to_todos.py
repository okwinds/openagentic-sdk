from __future__ import annotations

import asyncio

from _common import repo_root, require_env_simple, rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


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
        "IMPORTANT: You MUST call TodoWrite (with all 6 todos) before replying.\n"
        "Finally reply with RESEARCH_TODO_OK."
    )
    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
