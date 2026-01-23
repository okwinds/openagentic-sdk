from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ToolContext:
    cwd: str
    project_dir: str | None = None


class Tool:
    name: str
    description: str

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> Any:
        raise NotImplementedError

    def run_sync(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> Any:
        return asyncio.run(self.run(tool_input, ctx))
