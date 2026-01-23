from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from .base import ModelOutput, ToolCall
from .openai_stream_assembler import ToolCallAssembler
from .sse import parse_sse_events
from .stream_events import DoneEvent, TextDeltaEvent, ToolCallEvent


Transport = Callable[[str, Mapping[str, str], Mapping[str, Any]], Mapping[str, Any]]
StreamTransport = Callable[[str, Mapping[str, str], Mapping[str, Any]], Iterable[bytes]]


def _default_transport(url: str, headers: Mapping[str, str], payload: Mapping[str, Any], *, timeout_s: float) -> Mapping[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def _default_stream_transport(
    url: str, headers: Mapping[str, str], payload: Mapping[str, Any], *, timeout_s: float
) -> Iterable[bytes]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    resp = urllib.request.urlopen(req, timeout=timeout_s)
    try:
        while True:
            chunk = resp.readline()
            if not chunk:
                break
            yield chunk
    finally:
        resp.close()


def _iter_lines(chunks: Iterable[bytes]) -> Iterable[bytes]:
    buf = b""
    for chunk in chunks:
        if not chunk:
            continue
        buf += chunk
        while True:
            idx = buf.find(b"\n")
            if idx < 0:
                break
            line = buf[: idx + 1]
            buf = buf[idx + 1 :]
            yield line
    if buf:
        yield buf


@dataclass(frozen=True, slots=True)
class OpenAICompatibleProvider:
    name: str = "openai-compatible"
    base_url: str = "https://api.openai.com/v1"
    api_key_header: str = "authorization"
    timeout_s: float = 60.0
    transport: Transport | None = None
    stream_transport: StreamTransport | None = None

    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]] = (),
        api_key: str | None = None,
    ) -> ModelOutput:
        if not api_key:
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

        if self.transport is None:
            obj = _default_transport(url, headers, payload, timeout_s=self.timeout_s)
        else:
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

    async def stream(
        self,
        *,
        model: str,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]] = (),
        api_key: str | None = None,
    ):
        if not api_key:
            raise ValueError("OpenAICompatibleProvider: api_key is required")

        url = f"{self.base_url}/chat/completions"
        headers = {"content-type": "application/json"}
        if self.api_key_header.lower() == "authorization":
            headers["authorization"] = f"Bearer {api_key}"
        else:
            headers[self.api_key_header] = api_key

        payload: dict[str, Any] = {
            "model": model,
            "messages": list(messages),
            "stream": True,
        }
        if tools:
            payload["tools"] = list(tools)

        assembler = ToolCallAssembler()
        if self.stream_transport is None:
            chunks = _default_stream_transport(url, headers, payload, timeout_s=self.timeout_s)
        else:
            chunks = self.stream_transport(url, headers, payload)
        for data in parse_sse_events(_iter_lines(chunks)):
            if data.strip() == "[DONE]":
                for tc in assembler.finalize():
                    yield ToolCallEvent(tool_call=tc)
                yield DoneEvent()
                return
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            choice = (obj.get("choices") or [None])[0] or {}
            delta = choice.get("delta") or {}
            if isinstance(delta, dict):
                content = delta.get("content")
                if isinstance(content, str) and content:
                    yield TextDeltaEvent(delta=content)
                for tc in delta.get("tool_calls") or []:
                    if isinstance(tc, dict):
                        assembler.apply_delta(tc)

        for tc in assembler.finalize():
            yield ToolCallEvent(tool_call=tc)
        yield DoneEvent()
