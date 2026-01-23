from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class ReadTool(Tool):
    name: str = "Read"
    description: str = "Read a file from disk."
    max_bytes: int = 1024 * 1024

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        file_path = tool_input.get("file_path")
        if not isinstance(file_path, str) or not file_path:
            raise ValueError("Read: 'file_path' must be a non-empty string")

        p = Path(file_path)
        if not p.is_absolute():
            p = Path(ctx.cwd) / p
        data = p.read_bytes()
        if len(data) > self.max_bytes:
            data = data[: self.max_bytes]
        return {"file_path": str(p), "content": data.decode("utf-8", errors="replace")}
