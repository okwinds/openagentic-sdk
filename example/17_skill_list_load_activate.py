from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "CLAUDE.md").write_text("Project memory: demo", encoding="utf-8")
        (root / ".claude" / "skills" / "greeter").mkdir(parents=True)
        (root / ".claude" / "skills" / "greeter" / "SKILL.md").write_text(
            "# Greeter\n\nSays hello.\n\n## Checklist\n- Greet politely\n",
            encoding="utf-8",
        )

        options = rightcode_options(
            cwd=root,
            project_dir=root,
            allowed_tools=["SkillList", "SkillLoad", "SkillActivate"],
        )
        prompt = (
            "1) Call SkillList.\n"
            "2) Call SkillLoad with name='Greeter'.\n"
            "3) Call SkillActivate with name='Greeter'.\n"
            "Then reply with SKILL_OK and include the active skill list."
        )
        printer = ConsoleRenderer(debug=console_debug_enabled())
        await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
