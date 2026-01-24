from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    options = rightcode_options(
        cwd=repo_root(),
        project_dir=repo_root(),
        allowed_tools=["WebSearch"],
        permission_mode="bypass",
        interactive=False,
    )
    prompt = (
        "Use WebSearch with query='site:openai.com OpenAI developer docs tools' and max_results=5.\n"
        "Use allowed_domains=['openai.com'].\n"
        "Then reply with SEARCH_FILTER_OK and list the URLs you found."
    )
    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
