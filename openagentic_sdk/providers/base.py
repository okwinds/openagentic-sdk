from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Protocol, Sequence


@dataclass(frozen=True, slots=True)
class ToolCall:
    tool_use_id: str
    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ModelOutput:
    assistant_text: str | None
    tool_calls: Sequence[ToolCall]
    usage: Optional[Mapping[str, Any]] = None
    raw: Optional[Mapping[str, Any]] = None
    response_id: str | None = None
    provider_metadata: Optional[Mapping[str, Any]] = None


class Provider(Protocol):
    name: str

    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]] = (),
        api_key: str | None = None,
    ) -> ModelOutput: ...
