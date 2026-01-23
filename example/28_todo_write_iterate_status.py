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
        "You will update the TODO list in 3 steps using TodoWrite.\n"
        "Step 1: create 3 pending items.\n"
        "Step 2: update so exactly 1 item is in_progress.\n"
        "Step 3: update so all items are completed.\n"
        "After each step, call TodoWrite.\n"
        "Finally reply with TODO_ITER_OK."
    )
    printer = ConsoleRenderer(debug=console_debug_enabled())
    async for ev in query(prompt=prompt, options=options):
        printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())
