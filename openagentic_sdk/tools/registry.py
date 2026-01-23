from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .base import Tool


@dataclass(frozen=True, slots=True)
class ToolRegistry:
    _tools: dict[str, Tool]

    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        object.__setattr__(self, "_tools", {})
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        name = getattr(tool, "name", None)
        if not isinstance(name, str) or not name:
            raise ValueError("tool must have a non-empty string 'name'")
        self._tools[name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise KeyError(f"unknown tool: {name}") from None

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

