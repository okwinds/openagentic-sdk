from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    # This example uses the skills located at: example/.claude/skills/*
    project_dir = repo_root() / "example"
    options = rightcode_options(
        cwd=project_dir,
        project_dir=project_dir,
        allowed_tools=["Skill"],
        permission_mode="bypass",
        interactive=False,
    )

    prompt = "What Skills are available?"

    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
