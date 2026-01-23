from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class GlobTool(Tool):
    name: str = "Glob"
    description: str = "Find files by glob pattern."

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        pattern = tool_input.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("Glob: 'pattern' must be a non-empty string")
        root = tool_input.get("root")
        base = Path(ctx.cwd) if root is None else Path(root)
        matches = [str(p) for p in sorted(base.glob(pattern))]
        return {"root": str(base), "matches": matches}
