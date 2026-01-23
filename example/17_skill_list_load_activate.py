from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import query


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
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())
