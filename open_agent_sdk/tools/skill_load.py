from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..skills.index import index_skills
from ..skills.parse import parse_skill_markdown
from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class SkillLoadTool(Tool):
    name: str = "SkillLoad"
    description: str = "Load a skill's SKILL.md by name."

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        name = tool_input.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("SkillLoad: 'name' must be a non-empty string")

        project_dir = tool_input.get("project_dir")
        base = Path(ctx.project_dir or ctx.cwd) if project_dir is None else Path(str(project_dir))
        skills = index_skills(project_dir=str(base))
        match = next((s for s in skills if s.name == name), None)
        if match is None:
            raise FileNotFoundError(f"SkillLoad: skill not found: {name}")

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
