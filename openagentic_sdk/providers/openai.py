from __future__ import annotations

from dataclasses import dataclass

from .openai_responses import OpenAIResponsesProvider


@dataclass(frozen=True, slots=True)
class OpenAIProvider(OpenAIResponsesProvider):
    name: str = "openai"
    api_key_header: str = "authorization"

