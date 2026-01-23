from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class SkillActivateTool(Tool):
    name: str = "SkillActivate"
    description: str = "Activate a skill for the current session (runtime-managed)."

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        _ = ctx
        name = tool_input.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("SkillActivate: 'name' must be a non-empty string")
        # Activation state is persisted by the runtime via events.
        return {"requested": name}

