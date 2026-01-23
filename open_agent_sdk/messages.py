from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence


# Content blocks


@dataclass(frozen=True, slots=True)
class TextBlock:
    type: Literal["text"] = "text"
    text: str = ""


@dataclass(frozen=True, slots=True)
class ThinkingBlock:
    type: Literal["thinking"] = "thinking"
    thinking: str = ""
    signature: str = ""


@dataclass(frozen=True, slots=True)
class ToolUseBlock:
    type: Literal["tool_use"] = "tool_use"
    id: str = ""
    name: str = ""
    input: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolResultBlock:
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = ""
    content: str | Sequence[Mapping[str, Any]] | None = None
    is_error: bool | None = None


ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock


# Messages


@dataclass(frozen=True, slots=True)
class UserMessage:
    content: str | list[ContentBlock]


@dataclass(frozen=True, slots=True)
class AssistantMessage:
    content: list[ContentBlock]
    model: str


@dataclass(frozen=True, slots=True)
class SystemMessage:
    subtype: str
    data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ResultMessage:
    subtype: str
    duration_ms: int
    duration_api_ms: int
    is_error: bool
    num_turns: int
    session_id: str
    total_cost_usd: float | None = None
    usage: dict[str, Any] | None = None
    result: str | None = None
    structured_output: Any = None


@dataclass(frozen=True, slots=True)
class StreamEvent:
    uuid: str
    session_id: str
    event: dict[str, Any]
    parent_tool_use_id: str | None = None


Message = UserMessage | AssistantMessage | SystemMessage | ResultMessage | StreamEvent

