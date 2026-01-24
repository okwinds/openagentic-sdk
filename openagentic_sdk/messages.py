from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

# Content blocks


def _compact(value: Any, *, max_len: int = 200) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        s = value
    else:
        try:
            s = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        except Exception:  # noqa: BLE001
            s = str(value)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = " ".join(s.splitlines()).strip()
    if len(s) > max_len:
        return s[: max(0, max_len - 1)] + "…"
    return s


@dataclass(frozen=True, slots=True)
class TextBlock:
    type: Literal["text"] = "text"
    text: str = ""

    def __str__(self) -> str:  # pragma: no cover (trivial)
        return self.text


@dataclass(frozen=True, slots=True)
class ThinkingBlock:
    type: Literal["thinking"] = "thinking"
    thinking: str = ""
    signature: str = ""

    def __str__(self) -> str:  # pragma: no cover (trivial)
        # Thinking is typically not user-facing.
        return ""


@dataclass(frozen=True, slots=True)
class ToolUseBlock:
    type: Literal["tool_use"] = "tool_use"
    id: str = ""
    name: str = ""
    input: Mapping[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        inp = _compact(self.input) if self.input else ""
        core = f"[tool.use] {self.name}".strip()
        if self.id:
            core += f" id={self.id}"
        if inp:
            core += f" input={inp}"
        return core


@dataclass(frozen=True, slots=True)
class ToolResultBlock:
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = ""
    content: str | Sequence[Mapping[str, Any]] | None = None
    is_error: bool | None = None

    def __str__(self) -> str:
        status = "error" if self.is_error else "ok"
        core = f"[tool.result] {self.tool_use_id} {status}".strip()
        c = _compact(self.content)
        if c:
            core += f" content={c}"
        return core


ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock


# Messages


@dataclass(frozen=True, slots=True)
class UserMessage:
    content: str | list[ContentBlock]

    def __str__(self) -> str:
        if isinstance(self.content, str):
            return self.content
        parts = [str(b) for b in self.content]
        return "\n".join([p for p in parts if p])


@dataclass(frozen=True, slots=True)
class AssistantMessage:
    content: list[ContentBlock]
    model: str

    def __str__(self) -> str:
        if len(self.content) == 1:
            return str(self.content[0])
        parts = [str(b) for b in self.content]
        return "\n".join([p for p in parts if p])


@dataclass(frozen=True, slots=True)
class SystemMessage:
    subtype: str
    data: dict[str, Any]

    def __str__(self) -> str:
        data = _compact(self.data)
        core = f"[system.{self.subtype}]".strip()
        if data:
            core += f" {data}"
        return core


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

    def __str__(self) -> str:
        # Avoid duplicating the final assistant text (which is already emitted separately).
        core = "[done]"
        if self.session_id:
            core += f" session_id={self.session_id}"
        if self.is_error:
            core += " error=True"
        return core


@dataclass(frozen=True, slots=True)
class StreamEvent:
    uuid: str
    session_id: str
    event: dict[str, Any]
    parent_tool_use_id: str | None = None

    def __str__(self) -> str:
        # For streaming, callers likely want `print(msg, end="")` when type is text_delta.
        if self.event.get("type") == "text_delta":
            delta = self.event.get("delta")
            return delta if isinstance(delta, str) else _compact(delta)
        return f"[stream] {_compact(self.event)}"


Message = UserMessage | AssistantMessage | SystemMessage | ResultMessage | StreamEvent
