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


class LegacyProvider(Protocol):
    """Chat-completions style providers (messages in, no response_id threading)."""

    @property
    def name(self) -> str: ...

    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]] = (),
        api_key: str | None = None,
    ) -> ModelOutput: ...


class ResponsesProvider(Protocol):
    """Responses API style providers (input[] in, previous_response_id threading)."""

    @property
    def name(self) -> str: ...

    async def complete(
        self,
        *,
        model: str,
        input: Sequence[Mapping[str, Any]],
        instructions: str | None = None,
        tools: Sequence[Mapping[str, Any]] = (),
        api_key: str | None = None,
        previous_response_id: str | None = None,
        store: bool = True,
        include: Sequence[str] = (),
    ) -> ModelOutput: ...


Provider = LegacyProvider | ResponsesProvider
