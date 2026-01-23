from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from .base import ModelOutput, ToolCall
from .openai_stream_assembler import ToolCallAssembler
from .sse import parse_sse_events
from .stream_events import DoneEvent, TextDeltaEvent, ToolCallEvent


Transport = Callable[[str, Mapping[str, str], Mapping[str, Any]], Mapping[str, Any]]
StreamTransport = Callable[[str, Mapping[str, str], Mapping[str, Any]], Iterable[bytes]]

_RETRYABLE_HTTP_STATUS: set[int] = {408, 409, 425, 429, 500, 502, 503, 504}


def _backoff_seconds(attempt_index: int, base: float) -> float:
    # attempt_index: 0 for first retry, 1 for second retry, ...
    if attempt_index < 0:
        return 0.0
    return max(0.0, base) * (2**attempt_index)


def _read_http_error_body(e: urllib.error.HTTPError) -> str:
    try:
        return e.read().decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def _runtime_http_error(url: str, e: urllib.error.HTTPError) -> RuntimeError:
    body = _read_http_error_body(e)
    hint = " (transient upstream error; try again)" if int(getattr(e, "code", 0)) in _RETRYABLE_HTTP_STATUS else ""
    return RuntimeError(f"HTTP {e.code} from {url}{hint}: {body}".strip())


def _default_transport(
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    *,
    timeout_s: float,
    max_retries: int = 0,
    retry_backoff_s: float = 0.5,
) -> Mapping[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    last_exc: Exception | None = None
    max_retries = max(0, int(max_retries))
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read()
            break
        except urllib.error.HTTPError as e:
            last_exc = e
            if attempt < max_retries and int(getattr(e, "code", 0)) in _RETRYABLE_HTTP_STATUS:
                time.sleep(_backoff_seconds(attempt, retry_backoff_s))
                continue
            raise _runtime_http_error(url, e) from e
        except urllib.error.URLError as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(_backoff_seconds(attempt, retry_backoff_s))
                continue
            raise RuntimeError(f"Request failed to {url}: {e}".strip()) from e
    else:  # pragma: no cover
        raise RuntimeError(f"Request failed to {url}: {last_exc}".strip()) from last_exc
    return json.loads(raw.decode("utf-8"))


def _default_stream_transport(
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    *,
    timeout_s: float,
    max_retries: int = 0,
    retry_backoff_s: float = 0.5,
) -> Iterable[bytes]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    max_retries = max(0, int(max_retries))
    resp = None
    for attempt in range(max_retries + 1):
        try:
            resp = urllib.request.urlopen(req, timeout=timeout_s)
            break
        except urllib.error.HTTPError as e:
            if attempt < max_retries and int(getattr(e, "code", 0)) in _RETRYABLE_HTTP_STATUS:
                time.sleep(_backoff_seconds(attempt, retry_backoff_s))
                continue
            raise _runtime_http_error(url, e) from e
        except urllib.error.URLError as e:
            if attempt < max_retries:
                time.sleep(_backoff_seconds(attempt, retry_backoff_s))
                continue
            raise RuntimeError(f"Request failed to {url}: {e}".strip()) from e
    if resp is None:  # pragma: no cover
        raise RuntimeError(f"Request failed to {url}".strip())
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
    max_retries: int = 0
    retry_backoff_s: float = 0.5
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
