from __future__ import annotations

from typing import Any, AsyncIterable


async def coerce_prompt(prompt: str | AsyncIterable[dict[str, Any]]) -> str:
    if isinstance(prompt, str):
        return prompt

    parts: list[str] = []
    async for chunk in prompt:
        if not isinstance(chunk, dict):
            raise TypeError("prompt stream items must be dicts")
        if chunk.get("type") != "text":
            raise ValueError("only {type:'text', text:'...'} streaming prompts are supported")
        text = chunk.get("text")
        if not isinstance(text, str):
            raise TypeError("prompt stream 'text' must be a string")
        parts.append(text)
    return "\n".join(parts)

