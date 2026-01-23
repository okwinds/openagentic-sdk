from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options

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
        async for ev in query(prompt=prompt, options=options):
            if ev.type == "assistant.delta":
                print(ev.text_delta, end="", flush=True)
            elif ev.type == "assistant.message":
                print()
                print(ev.text)
            elif ev.type == "tool.use":
                print(f"\n[tool.use] {ev.name} {ev.input}")
            elif ev.type == "tool.result":
                print(f"[tool.result] error={ev.is_error} output={ev.output}")
            elif ev.type == "skill.activated":
                print(f"[skill.activated] {ev.name}")
            elif ev.type == "result":
                print(f"[result] session_id={ev.session_id} stop_reason={ev.stop_reason}")


if __name__ == "__main__":
    asyncio.run(main())
