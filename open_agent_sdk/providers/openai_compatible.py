from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence

from .base import ModelOutput, ToolCall


Transport = Callable[[str, Mapping[str, str], Mapping[str, Any]], Mapping[str, Any]]


def _default_transport(url: str, headers: Mapping[str, str], payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


@dataclass(frozen=True, slots=True)
class OpenAICompatibleProvider:
    name: str = "openai-compatible"
    base_url: str = "https://api.openai.com/v1"
    api_key_header: str = "authorization"
    transport: Transport = _default_transport

    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]] = (),
        api_key: str | None = None,
    ) -> ModelOutput:
        if api_key is None:
            raise ValueError("OpenAICompatibleProvider: api_key is required")

        url = f"{self.base_url}/chat/completions"
        headers = {"content-type": "application/json"}
        if self.api_key_header.lower() == "authorization":
            headers["authorization"] = f"Bearer {api_key}"
        else:
            headers[self.api_key_header] = api_key

        payload: dict[str, Any] = {"model": model, "messages": list(messages)}
        if tools:
            payload["tools"] = list(tools)

        obj = self.transport(url, headers, payload)
        choice = (obj.get("choices") or [None])[0] or {}
        message = choice.get("message") or {}

        assistant_text = message.get("content")
        if assistant_text is not None and not isinstance(assistant_text, str):
            assistant_text = str(assistant_text)

        tool_calls_out: list[ToolCall] = []
        for tc in message.get("tool_calls") or []:
            if not isinstance(tc, dict):
                continue
            tool_use_id = tc.get("id") or ""
            fn = tc.get("function") or {}
            name = fn.get("name") or ""
            args_raw = fn.get("arguments") or "{}"
            if isinstance(args_raw, str):
                try:
                    args = json.loads(args_raw) if args_raw.strip() else {}
                except json.JSONDecodeError:
                    args = {"_raw": args_raw}
            elif isinstance(args_raw, dict):
                args = args_raw
            else:
                args = {"_raw": args_raw}
            tool_calls_out.append(ToolCall(tool_use_id=str(tool_use_id), name=str(name), arguments=args))

        return ModelOutput(
            assistant_text=assistant_text,
            tool_calls=tool_calls_out,
            usage=obj.get("usage") if isinstance(obj.get("usage"), dict) else None,
            raw=obj if isinstance(obj, dict) else None,
        )

