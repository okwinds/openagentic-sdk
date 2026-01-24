from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

from .base import ModelOutput, ToolCall
from .openai_compatible import _default_stream_transport, _default_transport  # noqa: PLC2701
from .sse import parse_sse_events
from .stream_events import DoneEvent, TextDeltaEvent, ToolCallEvent

Transport = Callable[[str, Mapping[str, str], Mapping[str, Any]], Mapping[str, Any]]
StreamTransport = Callable[[str, Mapping[str, str], Mapping[str, Any]], Iterable[bytes]]


def _build_headers(*, api_key_header: str, api_key: str) -> dict[str, str]:
    headers = {"content-type": "application/json"}
    if api_key_header.lower() == "authorization":
        headers["authorization"] = f"Bearer {api_key}"
    else:
        headers[api_key_header] = api_key
    return headers


def _parse_tool_call(item: Mapping[str, Any]) -> ToolCall | None:
    call_id = item.get("call_id")
    name = item.get("name")
    args_raw = item.get("arguments")
    if not isinstance(call_id, str) or not call_id:
        return None
    if not isinstance(name, str) or not name:
        return None
    args: dict[str, Any]
    if isinstance(args_raw, str):
        try:
            args = json.loads(args_raw) if args_raw.strip() else {}
        except json.JSONDecodeError:
            args = {"_raw": args_raw}
    elif isinstance(args_raw, dict):
        args = dict(args_raw)
    else:
        args = {"_raw": args_raw}
    return ToolCall(tool_use_id=call_id, name=name, arguments=args)


def _parse_assistant_text(output_items: Sequence[Mapping[str, Any]]) -> str | None:
    parts: list[str] = []
    for item in output_items:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
    if not parts:
        return None
    return "".join(parts)


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
class OpenAIResponsesProvider:
    name: str = "openai-responses"
    base_url: str = "https://api.openai.com/v1"
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
        if not api_key:
            raise ValueError("OpenAIResponsesProvider: api_key is required")

        url = f"{self.base_url}/responses"
        headers = _build_headers(api_key_header=self.api_key_header, api_key=api_key)

        payload: dict[str, Any] = {"model": model, "input": list(input), "store": bool(store)}
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
        if include:
            payload["include"] = list(include)
        if tools:
            payload["tools"] = list(tools)

        if self.transport is None:
            obj = _default_transport(
                url,
                headers,
                payload,
                timeout_s=self.timeout_s,
                max_retries=self.max_retries,
                retry_backoff_s=self.retry_backoff_s,
            )
        else:
            obj = self.transport(url, headers, payload)

        output = obj.get("output")
        output_items: list[Mapping[str, Any]] = [x for x in (output or []) if isinstance(x, dict)]

        assistant_text = _parse_assistant_text(output_items)
        tool_calls: list[ToolCall] = []
        for item in output_items:
            if item.get("type") == "function_call":
                tc = _parse_tool_call(item)
                if tc is not None:
                    tool_calls.append(tc)

        response_id = obj.get("id") if isinstance(obj.get("id"), str) else None
        usage = obj.get("usage") if isinstance(obj.get("usage"), dict) else None
        raw = obj if isinstance(obj, dict) else None
        return ModelOutput(
            assistant_text=assistant_text,
            tool_calls=tool_calls,
            usage=usage,
            raw=raw,
            response_id=response_id,
            provider_metadata=None,
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
    ):
        if not api_key:
            raise ValueError("OpenAIResponsesProvider: api_key is required")

        url = f"{self.base_url}/responses"
        headers = _build_headers(api_key_header=self.api_key_header, api_key=api_key)

        payload: dict[str, Any] = {"model": model, "input": list(input), "stream": True, "store": bool(store)}
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
        if include:
            payload["include"] = list(include)
        if tools:
            payload["tools"] = list(tools)

        if self.stream_transport is None:
            chunks = _default_stream_transport(
                url,
                headers,
                payload,
                timeout_s=self.timeout_s,
                max_retries=self.max_retries,
                retry_backoff_s=self.retry_backoff_s,
            )
        else:
            chunks = self.stream_transport(url, headers, payload)

        response_id: str | None = None
        usage: Mapping[str, Any] | None = None
        ongoing: dict[int, dict[str, Any]] = {}
        for data in parse_sse_events(_iter_lines(chunks)):
            if data.strip() == "[DONE]":
                yield DoneEvent(response_id=response_id, usage=usage)
                return
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            typ = obj.get("type")
            if not isinstance(typ, str):
                continue

            # Some gateways include `response_id` on every event (and may omit `response.created`).
            rid0 = obj.get("response_id")
            if isinstance(rid0, str) and rid0:
                response_id = rid0

            if typ == "response.created":
                resp = obj.get("response")
                if isinstance(resp, dict):
                    rid = resp.get("id")
                    if isinstance(rid, str) and rid:
                        response_id = rid
                continue

            if typ == "response.output_text.delta":
                delta = obj.get("delta")
                if isinstance(delta, str) and delta:
                    yield TextDeltaEvent(delta=delta)
                continue

            if typ == "response.output_item.added":
                output_index = obj.get("output_index")
                item = obj.get("item")
                if isinstance(output_index, int) and isinstance(item, dict) and item.get("type") == "function_call":
                    call_id = item.get("call_id")
                    name = item.get("name")
                    if isinstance(call_id, str) and call_id and isinstance(name, str) and name:
                        ongoing[output_index] = {"call_id": call_id, "name": name, "arguments": ""}
                continue

            if typ == "response.function_call_arguments.delta":
                output_index = obj.get("output_index")
                delta = obj.get("delta")
                if isinstance(output_index, int) and isinstance(delta, str) and output_index in ongoing:
                    ongoing[output_index]["arguments"] += delta
                continue

            if typ == "response.output_item.done":
                output_index = obj.get("output_index")
                item = obj.get("item")
                if isinstance(output_index, int) and isinstance(item, dict) and item.get("type") == "function_call":
                    st = ongoing.get(output_index) or {}
                    tc = _parse_tool_call(
                        {
                            "call_id": st.get("call_id") or item.get("call_id"),
                            "name": st.get("name") or item.get("name"),
                            "arguments": st.get("arguments") or item.get("arguments") or "",
                        }
                    )
                    if tc is not None:
                        yield ToolCallEvent(tool_call=tc)
                    ongoing.pop(output_index, None)
                continue

            if typ in ("response.completed", "response.incomplete"):
                resp = obj.get("response")
                if isinstance(resp, dict):
                    rid = resp.get("id")
                    if isinstance(rid, str) and rid:
                        response_id = rid
                    u = resp.get("usage")
                    if isinstance(u, dict):
                        usage = u
                yield DoneEvent(response_id=response_id, usage=usage)
                return

        yield DoneEvent(response_id=response_id, usage=usage)
