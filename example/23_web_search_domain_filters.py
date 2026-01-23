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
        allowed_tools=["WebSearch"],
        permission_mode="bypass",
        interactive=False,
    )
    prompt = (
        "Use WebSearch with query='OpenAI developer docs tools' and max_results=5.\n"
        "Use allowed_domains=['openai.com'].\n"
        "Then reply with SEARCH_FILTER_OK and list the URLs you found."
    )
    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
