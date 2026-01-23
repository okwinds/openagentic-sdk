from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled

from open_agent_sdk import query


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
    async for ev in query(prompt=prompt, options=options):
        printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())
