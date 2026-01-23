from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    # This example uses the skills located at: example/.claude/skills/*
    project_dir = repo_root() / "example"
    options = rightcode_options(
        cwd=project_dir,
        project_dir=project_dir,
        allowed_tools=["SkillList", "SkillLoad", "SkillActivate"],
        permission_mode="bypass",
        interactive=False,
    )
    prompt = (
        "Execute the `main-process` skill from .claude/skills.\n"
        "Steps:\n"
        "1) Call SkillList to confirm `main-process` exists.\n"
        "2) Call SkillLoad name='main-process'. Read its workflow.\n"
        "3) Call SkillActivate name='main-process'.\n"
        "4) Follow the skill: print exactly: 主流程正在执行中...\n"
        "5) The skill says to delegate to the drawing skill and draw a Hello World graphic.\n"
        "   - Call SkillLoad name='drawing' (optional: SkillActivate name='drawing').\n"
        "   - Produce a clear ASCII-art 'Hello World' graphic (not code), 8+ lines.\n"
        "Finally reply with MAIN_PROCESS_OK."
    )
    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
