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
        "Call WebFetch with url='https://httpbin.org/json' and prompt='Extract the slideshow title and list slide titles. "
        "Include token JSON_OK.'. Then reply with the extracted data."
    )
    printer = ConsoleRenderer(debug=console_debug_enabled())
    async for ev in query(prompt=prompt, options=options):
        printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())
