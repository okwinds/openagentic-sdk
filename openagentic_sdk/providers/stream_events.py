from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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

