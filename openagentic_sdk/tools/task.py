from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class TaskTool(Tool):
    name: str = "Task"
    description: str = "Run a subagent (runtime-managed)."

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        _ = (tool_input, ctx)
        # The runtime handles this tool to integrate with host UX and to attach
        # sub-agent session metadata.
        return {"status": "requested"}
