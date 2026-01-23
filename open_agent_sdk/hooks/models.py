from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping, Optional


HookCallback = Callable[[Mapping[str, Any]], Awaitable["HookDecision"]]


@dataclass(frozen=True, slots=True)
class HookDecision:
    block: bool = False
    block_reason: str | None = None
    override_tool_input: Optional[Mapping[str, Any]] = None
    override_tool_output: Any = None
    override_messages: Optional[list[Mapping[str, Any]]] = None
    action: str | None = None


@dataclass(frozen=True, slots=True)
class HookMatcher:
    name: str
    tool_name_pattern: str = "*"
    hook: HookCallback | None = None

