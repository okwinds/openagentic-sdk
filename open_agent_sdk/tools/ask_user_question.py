from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class AskUserQuestionTool(Tool):
    name: str = "AskUserQuestion"
    description: str = "Ask the user a clarifying question (runtime-managed)."

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        _ = (tool_input, ctx)
        # The runtime handles this tool to integrate with host UX.
        return {"status": "requested"}

