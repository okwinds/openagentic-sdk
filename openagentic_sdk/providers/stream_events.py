from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from .base import ToolCall


@dataclass(frozen=True, slots=True)
class TextDeltaEvent:
    type: Literal["text_delta"] = "text_delta"
    delta: str = ""


@dataclass(frozen=True, slots=True)
class ToolCallEvent:
    type: Literal["tool_call"] = "tool_call"
    tool_call: ToolCall | None = None


@dataclass(frozen=True, slots=True)
class DoneEvent:
    type: Literal["done"] = "done"
    response_id: str | None = None
    usage: Mapping[str, Any] | None = None
