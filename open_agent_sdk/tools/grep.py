from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class GrepTool(Tool):
    name: str = "Grep"
    description: str = "Search file contents with a regex."
    max_matches: int = 5000

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        query = tool_input.get("query")
        if not isinstance(query, str) or not query:
            raise ValueError("Grep: 'query' must be a non-empty string")
        file_glob = tool_input.get("file_glob", "**/*")
        if not isinstance(file_glob, str) or not file_glob:
            raise ValueError("Grep: 'file_glob' must be a non-empty string")

        root_in = tool_input.get("root")
        root = Path(ctx.cwd) if root_in is None else Path(str(root_in))

        flags = 0 if tool_input.get("case_sensitive", True) else re.IGNORECASE
        rx = re.compile(query, flags=flags)

        matches: list[dict[str, Any]] = []
        for p in root.glob(file_glob):
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for idx, line in enumerate(text.splitlines(), start=1):
                if rx.search(line):
                    matches.append({"file_path": str(p), "line": idx, "text": line})
                    if len(matches) >= self.max_matches:
                        return {"root": str(root), "query": query, "matches": matches, "truncated": True}
        return {"root": str(root), "query": query, "matches": matches, "truncated": False}
