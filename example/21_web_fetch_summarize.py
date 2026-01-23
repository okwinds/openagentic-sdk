from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled

from open_agent_sdk import query


async def main() -> None:
    options = rightcode_options(
        cwd=repo_root(),
        project_dir=repo_root(),
        allowed_tools=["WebFetch"],
        permission_mode="bypass",
        interactive=False,
    )
    prompt = (
        "Call WebFetch with url='https://blog.lemonhall.me/notesview/show/667' and prompt='Summarize the page in 2 sentences.用中文回复 "
        "Include token FETCH_OK.'. Then return the tool response."
    )
    printer = ConsoleRenderer(debug=console_debug_enabled())
    async for ev in query(prompt=prompt, options=options):
        printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())
