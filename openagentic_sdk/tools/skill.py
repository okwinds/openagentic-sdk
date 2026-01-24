from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..skills.index import index_skills
from ..skills.parse import parse_skill_markdown, strip_frontmatter
from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class SkillTool(Tool):
    """
    OpenCode-style skill tool:
    - available skills are listed in the tool description (<available_skills>)
    - tool call loads a specific skill by name
    """

    name: str = "Skill"
    description: str = "Load a Skill by name."

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        name = tool_input.get("name")
        project_dir = tool_input.get("project_dir")

        base_in: str | None
        if isinstance(project_dir, str):
            base_in = project_dir.strip() or None
        else:
            base_in = None

        if base_in is None:
            base = Path(ctx.project_dir or ctx.cwd)
        else:
            p = Path(base_in)
            base = p if p.is_absolute() else Path(ctx.project_dir or ctx.cwd) / p

        name2 = name.strip() if isinstance(name, str) else ""

        if not name2:
            raise ValueError("Skill: 'name' must be a non-empty string")

        skills = index_skills(project_dir=str(base))
        match = next((s for s in skills if s.name == name2), None)
        if match is None:
            available = ", ".join([s.name for s in skills])
            raise FileNotFoundError(f"Skill: not found: {name2}. Available skills: {available or 'none'}")

        path = Path(match.path)
        content = path.read_text(encoding="utf-8", errors="replace")
        doc = parse_skill_markdown(content)
        body = strip_frontmatter(content).strip()
        base_dir = str(path.parent)
        output = "\n".join(
            [
                f"## Skill: {match.name}",
                "",
                f"**Base directory**: {base_dir}",
                "",
                body,
            ]
        ).strip()
        return {
            "title": f"Loaded skill: {match.name}",
            "output": output,
            "metadata": {"name": match.name, "dir": base_dir},
            "name": match.name,
            "description": doc.description,
            "summary": doc.summary,
            "checklist": list(doc.checklist),
            "path": str(path),
        }
