from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Optional


@dataclass(frozen=True, slots=True)
class EventBase:
    type: str
    ts: float | None = None
    seq: int | None = None


@dataclass(frozen=True, slots=True)
class SystemInit(EventBase):
    type: Literal["system.init"] = "system.init"
    session_id: str = ""
    cwd: str = ""
    sdk_version: str = ""
    parent_tool_use_id: str | None = None
    agent_name: str | None = None
    options_summary: Optional[Mapping[str, Any]] = None
    enabled_tools: Optional[list[str]] = None
    enabled_providers: Optional[list[str]] = None


@dataclass(frozen=True, slots=True)
class UserMessage(EventBase):
    type: Literal["user.message"] = "user.message"
    text: str = ""
    parent_tool_use_id: str | None = None
    agent_name: str | None = None


@dataclass(frozen=True, slots=True)
class UserQuestion(EventBase):
    type: Literal["user.question"] = "user.question"
    question_id: str = ""
    prompt: str = ""
    choices: list[str] = field(default_factory=list)
    parent_tool_use_id: str | None = None
    agent_name: str | None = None


@dataclass(frozen=True, slots=True)
class AssistantDelta(EventBase):
    type: Literal["assistant.delta"] = "assistant.delta"
    text_delta: str = ""
    parent_tool_use_id: str | None = None
    agent_name: str | None = None


@dataclass(frozen=True, slots=True)
class AssistantMessage(EventBase):
    type: Literal["assistant.message"] = "assistant.message"
    text: str = ""
    parent_tool_use_id: str | None = None
    agent_name: str | None = None


@dataclass(frozen=True, slots=True)
class ToolUse(EventBase):
    type: Literal["tool.use"] = "tool.use"
    tool_use_id: str = ""
    name: str = ""
    input: Mapping[str, Any] | None = None
    parent_tool_use_id: str | None = None
    agent_name: str | None = None


@dataclass(frozen=True, slots=True)
class ToolResult(EventBase):
    type: Literal["tool.result"] = "tool.result"
    tool_use_id: str = ""
    output: Any = None
    is_error: bool = False
    error_type: str | None = None
    error_message: str | None = None
    parent_tool_use_id: str | None = None
    agent_name: str | None = None


@dataclass(frozen=True, slots=True)
class Result(EventBase):
    type: Literal["result"] = "result"
    final_text: str = ""
    session_id: str = ""
    stop_reason: str | None = None
    usage: Mapping[str, Any] | None = None
    steps: int | None = None
    parent_tool_use_id: str | None = None
    agent_name: str | None = None


@dataclass(frozen=True, slots=True)
class HookEvent(EventBase):
    type: Literal["hook.event"] = "hook.event"
    hook_point: str = ""
    name: str = ""
    matched: bool = True
    duration_ms: float | None = None
    action: str | None = None


Event = (
    SystemInit
    | UserMessage
    | UserQuestion
    | AssistantDelta
    | AssistantMessage
    | ToolUse
    | ToolResult
    | HookEvent
    | Result
)
