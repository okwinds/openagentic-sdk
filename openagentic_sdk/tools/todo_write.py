from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .base import Tool, ToolContext

_STATUSES = ("pending", "in_progress", "completed")


@dataclass(frozen=True, slots=True)
class TodoWriteTool(Tool):
    name: str = "TodoWrite"
    description: str = "Write or update a TODO list for the current session."

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        _ = ctx
        todos = tool_input.get("todos")
        if not isinstance(todos, list) or not todos:
            raise ValueError("TodoWrite: 'todos' must be a non-empty list")

        pending = 0
        in_progress = 0
        completed = 0
        for t in todos:
            if not isinstance(t, dict):
                raise ValueError("TodoWrite: each todo must be an object")
            content = t.get("content")
            active_form = t.get("activeForm")
            status = t.get("status")
            if not isinstance(content, str) or not content:
                raise ValueError("TodoWrite: todo 'content' must be a non-empty string")
            if not isinstance(active_form, str) or not active_form:
                raise ValueError("TodoWrite: todo 'activeForm' must be a non-empty string")
            if status not in _STATUSES:
                raise ValueError("TodoWrite: todo 'status' must be 'pending', 'in_progress', or 'completed'")

            if status == "pending":
                pending += 1
            elif status == "in_progress":
                in_progress += 1
            else:
                completed += 1

        total = len(todos)
        return {
            "message": "Updated todos",
            "stats": {
                "total": total,
                "pending": pending,
                "in_progress": in_progress,
                "completed": completed,
            },
        }

