from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..skills.index import index_skills
from ..skills.parse import parse_skill_markdown
from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class SkillTool(Tool):
    """
    CAS-style single skill tool:
    - If called with no name (or action='list'): list available skills
    - If called with name (or action='load'): load the skill content
    """

    name: str = "Skill"
    description: str = "List or load Skills from .claude/skills/**/SKILL.md."

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        action = tool_input.get("action")
        name = tool_input.get("name")
        project_dir = tool_input.get("project_dir")
        base = Path(ctx.project_dir or ctx.cwd) if project_dir is None else Path(str(project_dir))

        action2 = str(action).strip().lower() if isinstance(action, str) else ""

        if action2 in ("", "list") and not isinstance(name, str):
            skills = index_skills(project_dir=str(base))
            return {
                "skills": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "summary": s.summary,
                        "path": s.path,
                    }
                    for s in skills
                ]
            }

        if not isinstance(name, str) or not name:
            raise ValueError("Skill: 'name' must be a non-empty string for this action")

        if action2 not in ("", "load", "get", "read"):
            raise ValueError("Skill: 'action' must be 'list' or 'load'")

        skills = index_skills(project_dir=str(base))
        match = next((s for s in skills if s.name == name), None)
        if match is None:
            raise FileNotFoundError(f"Skill: not found: {name}")

        path = Path(match.path)
        content = path.read_text(encoding="utf-8", errors="replace")
        doc = parse_skill_markdown(content)
        return {
            "name": match.name,
            "description": doc.description,
            "summary": doc.summary,
            "checklist": list(doc.checklist),
            "content": content,
            "path": str(path),
        }

