from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    options = rightcode_options(
        cwd=repo_root(),
        project_dir=repo_root(),
        allowed_tools=["TodoWrite"],
        permission_mode="bypass",
        interactive=False,
    )
    prompt = (
        "Create a TODO list for: 'Ship a small Python CLI this afternoon'.\n"
        "Call TodoWrite with 5 items, exactly one item in_progress, the rest pending.\n"
        "Then reply with TODO_CREATE_OK and include the stats you got back."
    )
    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
