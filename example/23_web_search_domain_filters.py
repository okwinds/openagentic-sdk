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
        allowed_tools=["WebSearch"],
        permission_mode="bypass",
        interactive=False,
    )
    prompt = (
        "Use WebSearch with query='OpenAI developer docs tools' and max_results=5.\n"
        "Use allowed_domains=['openai.com'].\n"
        "Then reply with SEARCH_FILTER_OK and list the URLs you found."
    )
    printer = EventPrinter(debug=example_debug_enabled())
    async for ev in query(prompt=prompt, options=options):
        printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())

