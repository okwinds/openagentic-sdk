from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .base import ToolCall


@dataclass(slots=True)
class _ToolCallState:
    name: str | None = None
    arguments_str: str = ""


@dataclass(slots=True)
class ToolCallAssembler:
    _calls: dict[str, _ToolCallState] = field(default_factory=dict)

    def apply_delta(self, delta: dict[str, Any]) -> None:
        tool_use_id = delta.get("id")
        if not isinstance(tool_use_id, str) or not tool_use_id:
            return
        fn = delta.get("function")
        if not isinstance(fn, dict):
            return
        state = self._calls.setdefault(tool_use_id, _ToolCallState())
        name = fn.get("name")
        if state.name is None and isinstance(name, str) and name:
            state.name = name
        args = fn.get("arguments")
        if isinstance(args, str) and args:
            state.arguments_str += args

    def finalize(self) -> list[ToolCall]:
        out: list[ToolCall] = []
        for tool_use_id, state in self._calls.items():
            name = state.name or ""
            args_raw = state.arguments_str
            try:
                args = json.loads(args_raw) if args_raw.strip() else {}
            except json.JSONDecodeError:
                args = {"_raw": args_raw}
            if not isinstance(args, dict):
                args = {"_raw": args}
            out.append(ToolCall(tool_use_id=tool_use_id, name=name, arguments=args))
        return out

