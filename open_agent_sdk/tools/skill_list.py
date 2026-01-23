from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..skills.index import index_skills
from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class SkillListTool(Tool):
    name: str = "SkillList"
    description: str = "List skills from .claude/skills/**/SKILL.md."

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        project_dir = tool_input.get("project_dir")
        base = Path(ctx.project_dir or ctx.cwd) if project_dir is None else Path(str(project_dir))
        skills = index_skills(project_dir=str(base))
        return {"skills": [{"name": s.name, "description": s.description, "summary": s.summary, "path": s.path} for s in skills]}
