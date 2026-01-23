from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class SlashCommandTool(Tool):
    name: str = "SlashCommand"
    description: str = "Load a .claude slash command by name."

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        name = tool_input.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("SlashCommand: 'name' must be a non-empty string")

        project_dir = tool_input.get("project_dir")
        base = Path(ctx.project_dir or ctx.cwd) if project_dir is None else Path(str(project_dir))
        path = base / ".claude" / "commands" / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"SlashCommand: not found: {path}")
        return {"name": name, "path": str(path), "content": path.read_text(encoding="utf-8", errors="replace")}
