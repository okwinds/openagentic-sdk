from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Iterable, Mapping, Sequence

from .base import ModelOutput
from .openai_responses import OpenAIResponsesProvider
from .stream_events import StreamEvent


Transport = Callable[[str, Mapping[str, str], Mapping[str, Any]], Mapping[str, Any]]
StreamTransport = Callable[[str, Mapping[str, str], Mapping[str, Any]], Iterable[bytes]]


@dataclass(frozen=True, slots=True)
class ResponsesProviderAlias:
    """A provider wrapper with a distinct name/default base_url.

    This is used to model non-OpenAI providers in deployments where they expose
    an OpenAI-compatible Responses API surface.
    """

    name: str
    base_url: str
    api_key_header: str = "authorization"
    timeout_s: float = 60.0
    max_retries: int = 0
    retry_backoff_s: float = 0.5
    transport: Transport | None = None
    stream_transport: StreamTransport | None = None

    async def complete(
        self,
        *,
        model: str,
        input: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]] = (),
        api_key: str | None = None,
        previous_response_id: str | None = None,
        store: bool = True,
        include: Sequence[str] = (),
    ) -> ModelOutput:
        inner = OpenAIResponsesProvider(
            name=self.name,
            base_url=self.base_url,
            api_key_header=self.api_key_header,
            timeout_s=self.timeout_s,
            max_retries=self.max_retries,
            retry_backoff_s=self.retry_backoff_s,
            transport=self.transport,
            stream_transport=self.stream_transport,
        )
        return await inner.complete(
            model=model,
            input=input,
            tools=tools,
            api_key=api_key,
            previous_response_id=previous_response_id,
            store=store,
            include=include,
        )

    async def stream(
        self,
        *,
        model: str,
        input: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]] = (),
        api_key: str | None = None,
        previous_response_id: str | None = None,
        store: bool = True,
        include: Sequence[str] = (),
    ) -> AsyncIterator[StreamEvent]:
        inner = OpenAIResponsesProvider(
            name=self.name,
            base_url=self.base_url,
            api_key_header=self.api_key_header,
            timeout_s=self.timeout_s,
            max_retries=self.max_retries,
            retry_backoff_s=self.retry_backoff_s,
            transport=self.transport,
            stream_transport=self.stream_transport,
        )
        async for ev in inner.stream(
            model=model,
            input=input,
            tools=tools,
            api_key=api_key,
            previous_response_id=previous_response_id,
            store=store,
            include=include,
        ):
            yield ev


def AnthropicProvider(**kwargs: Any) -> ResponsesProviderAlias:
    base_url = str(kwargs.pop("base_url", "https://api.anthropic.com/v1"))
    return ResponsesProviderAlias(name="anthropic", base_url=base_url, **kwargs)


def GeminiProvider(**kwargs: Any) -> ResponsesProviderAlias:
    base_url = str(kwargs.pop("base_url", "https://generativelanguage.googleapis.com/v1"))
    return ResponsesProviderAlias(name="gemini", base_url=base_url, **kwargs)


def QwenProvider(**kwargs: Any) -> ResponsesProviderAlias:
    base_url = str(kwargs.pop("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
    return ResponsesProviderAlias(name="qwen", base_url=base_url, **kwargs)
