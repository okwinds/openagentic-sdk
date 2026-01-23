from __future__ import annotations

import base64
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
        file_path = tool_input.get("file_path", tool_input.get("filePath"))
        if not isinstance(file_path, str) or not file_path:
            raise ValueError("Read: 'file_path' must be a non-empty string")

        p = Path(file_path)
        if not p.is_absolute():
            p = Path(ctx.cwd) / p

        offset = tool_input.get("offset")
        limit = tool_input.get("limit")
        if offset is not None and (not isinstance(offset, int) or offset < 1):
            raise ValueError("Read: 'offset' must be a positive integer (1-based)")
        if limit is not None and (not isinstance(limit, int) or limit < 0):
            raise ValueError("Read: 'limit' must be a non-negative integer")

        data = p.read_bytes()
        if len(data) > self.max_bytes:
            data = data[: self.max_bytes]

        # Image mode (best-effort): return base64 for common image types.
        suffix = p.suffix.lower()
        if suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            mime = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }.get(suffix, "application/octet-stream")
            return {
                "file_path": str(p),
                "image": base64.b64encode(data).decode("ascii"),
                "mime_type": mime,
                "file_size": len(data),
            }

        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines()

        # CAS compatibility: if offset/limit is provided, return line-numbered content.
        if offset is not None or limit is not None:
            start = (offset - 1) if isinstance(offset, int) else 0
            end = start + limit if isinstance(limit, int) else len(lines)
            slice_lines = lines[start:end]
            numbered = "\n".join(f"{i + 1}: {line}" for i, line in enumerate(slice_lines, start=start))
            return {
                "file_path": str(p),
                "content": numbered,
                "total_lines": len(lines),
                "lines_returned": len(slice_lines),
            }

        return {"file_path": str(p), "content": text}
