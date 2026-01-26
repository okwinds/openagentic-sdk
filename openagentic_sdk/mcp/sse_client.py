from __future__ import annotations

import asyncio
import http.client
import socket
import json
import threading
from urllib.parse import urlparse
from dataclasses import dataclass, field
from typing import Any, Mapping


def _conn_and_path(
    url: str, *, timeout_s: float
) -> tuple[http.client.HTTPConnection | http.client.HTTPSConnection, str]:
    u = urlparse(url)
    if u.scheme not in ("http", "https"):
        raise ValueError(f"unsupported url scheme: {u.scheme}")
    host = u.hostname
    if not host:
        raise ValueError("missing hostname")
    port = int(u.port) if u.port else (443 if u.scheme == "https" else 80)
    if u.scheme == "https":
        conn: http.client.HTTPConnection | http.client.HTTPSConnection = http.client.HTTPSConnection(host, port, timeout=float(timeout_s))
    else:
        conn = http.client.HTTPConnection(host, port, timeout=float(timeout_s))
    path = u.path or "/"
    if u.query:
        path = path + "?" + u.query
    return conn, path


def _post_json(url: str, payload: Mapping[str, Any], headers: Mapping[str, str] | None) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    conn, path = _conn_and_path(url, timeout_s=10.0)
    hdrs = {str(k): str(v) for k, v in (headers or {}).items()}
    hdrs.setdefault("Content-Type", "application/json")
    hdrs.setdefault("Accept", "application/json")
    hdrs["Content-Length"] = str(len(data))
    hdrs.setdefault("Connection", "close")
    conn.request("POST", path, body=data, headers=hdrs)
    resp = conn.getresponse()
    # Do not block waiting for a body.
    try:
        resp.read(0)
    finally:
        conn.close()


def _open_sse(url: str, headers: Mapping[str, str] | None) -> tuple[http.client.HTTPConnection | http.client.HTTPSConnection, Any]:
    # Keep the socket read timeout low so close() doesn't block for a full
    # network timeout when the reader is waiting for the next SSE line.
    conn, path = _conn_and_path(url, timeout_s=0.25)
    hdrs = {str(k): str(v) for k, v in (headers or {}).items()}
    hdrs.setdefault("Accept", "text/event-stream")
    conn.request("GET", path, headers=hdrs)
    resp = conn.getresponse()
    return conn, resp


@dataclass
class SseMcpClient:
    """Remote MCP client using SSE + /message POST.

    This follows the common MCP SSE transport convention:

    - GET  {base}/sse     (text/event-stream)
    - POST {base}/message (JSON-RPC request)
    """

    base_url: str
    headers: Mapping[str, str] | None = None

    _next_id: int = 1
    _pending: dict[int, asyncio.Future[Mapping[str, Any]]] = field(default_factory=dict)
    _pending_lock: threading.Lock = field(default_factory=threading.Lock)
    _started: bool = False
    _loop: asyncio.AbstractEventLoop | None = None
    _thread: threading.Thread | None = None
    _stop: threading.Event = field(default_factory=threading.Event)
    _connected: threading.Event = field(default_factory=threading.Event)
    _conn: http.client.HTTPConnection | http.client.HTTPSConnection | None = None
    _resp: Any | None = None

    @property
    def sse_url(self) -> str:
        return self.base_url.rstrip("/") + "/sse"

    @property
    def message_url(self) -> str:
        return self.base_url.rstrip("/") + "/message"

    def _dispatch(self, msg: Mapping[str, Any]) -> None:
        rid = msg.get("id")
        if not isinstance(rid, int):
            return
        with self._pending_lock:
            fut = self._pending.pop(rid, None)
        if fut is not None and not fut.done():
            fut.set_result(dict(msg))

    def _reader_thread(self) -> None:
        try:
            conn, resp = _open_sse(self.sse_url, self.headers)
            self._conn = conn
            self._resp = resp
            self._connected.set()
            buf: list[str] = []
            while not self._stop.is_set():
                fp = getattr(resp, "fp", None)
                if fp is None:
                    break
                try:
                    line_b = fp.readline()
                except socket.timeout:
                    continue
                if not line_b:
                    break
                line = line_b.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    # End of event.
                    if buf:
                        data = "\n".join(buf)
                        buf = []
                        try:
                            obj = json.loads(data)
                        except Exception:
                            continue
                        if isinstance(obj, dict) and self._loop is not None:
                            self._loop.call_soon_threadsafe(self._dispatch, obj)
                    continue
                if line.startswith(":"):
                    continue
                if line.startswith("data:"):
                    buf.append(line[len("data:") :].lstrip())
        except Exception as e:  # noqa: BLE001
            # Fail all pending requests.
            loop = self._loop
            with self._pending_lock:
                pending_items = list(self._pending.items())
                self._pending.clear()
            if loop is not None:
                for _rid, fut in pending_items:
                    if not fut.done():
                        loop.call_soon_threadsafe(fut.set_exception, e)
        finally:
            try:
                if self._resp is not None:
                    self._resp.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                if self._conn is not None:
                    self._conn.close()
            except Exception:  # noqa: BLE001
                pass

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._loop = asyncio.get_running_loop()
        self._stop.clear()
        self._connected.clear()
        t = threading.Thread(target=self._reader_thread, name="mcp-sse", daemon=True)
        self._thread = t
        t.start()

        # Best-effort: ensure the event stream is connected before sending the first request.
        await asyncio.to_thread(self._connected.wait, 2.0)

    async def close(self) -> None:
        self._stop.set()
        try:
            if self._resp is not None:
                self._resp.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            if self._conn is not None:
                self._conn.close()
        except Exception:  # noqa: BLE001
            pass
        t = self._thread
        if t is not None and t.is_alive():
            await asyncio.to_thread(t.join, 1.0)
        self._thread = None
        self._started = False

    async def _request(self, method: str, params: Mapping[str, Any] | None = None, *, timeout_s: float = 10.0) -> Mapping[str, Any]:
        await self.start()
        rid = self._next_id
        self._next_id += 1
        fut: asyncio.Future[Mapping[str, Any]] = asyncio.get_running_loop().create_future()
        with self._pending_lock:
            self._pending[rid] = fut

        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            payload["params"] = dict(params)
        await asyncio.to_thread(_post_json, self.message_url, payload, self.headers)
        return await asyncio.wait_for(fut, timeout=timeout_s)

    async def list_tools(self) -> list[dict[str, Any]]:
        resp = await self._request("tools/list")
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        result = resp.get("result")
        if not isinstance(result, dict):
            return []
        tools = result.get("tools")
        return list(tools) if isinstance(tools, list) else []

    async def call_tool(self, *, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        resp = await self._request("tools/call", params={"name": name, "arguments": dict(arguments)})
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        result = resp.get("result")
        if not isinstance(result, dict):
            return {"text": "", "raw": result}
        content = result.get("content")
        text_parts: list[str] = []
        content_list: list[dict[str, Any]] = []
        if isinstance(content, list):
            content_list = [c for c in content if isinstance(c, dict)]
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    t = item.get("text")
                    if isinstance(t, str):
                        text_parts.append(t)
        return {"text": "".join(text_parts), "content": content_list, "raw": result}

    async def list_prompts(self) -> list[dict[str, Any]]:
        resp = await self._request("prompts/list")
        if isinstance(resp.get("error"), dict):
            return []
        result = resp.get("result")
        if not isinstance(result, dict):
            return []
        prompts = result.get("prompts")
        return list(prompts) if isinstance(prompts, list) else []

    async def get_prompt(self, *, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        resp = await self._request("prompts/get", params={"name": name, "arguments": dict(arguments)})
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        result = resp.get("result")
        if not isinstance(result, dict):
            return {"text": "", "raw": result}
        content = result.get("content")
        text_parts: list[str] = []
        content_list: list[dict[str, Any]] = []
        if isinstance(content, list):
            content_list = [c for c in content if isinstance(c, dict)]
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    t = item.get("text")
                    if isinstance(t, str):
                        text_parts.append(t)
        return {"text": "".join(text_parts), "content": content_list, "raw": result}

    async def list_resources(self) -> list[dict[str, Any]]:
        resp = await self._request("resources/list")
        if isinstance(resp.get("error"), dict):
            return []
        result = resp.get("result")
        if not isinstance(result, dict):
            return []
        resources = result.get("resources")
        return list(resources) if isinstance(resources, list) else []

    async def read_resource(self, *, uri: str) -> dict[str, Any]:
        resp = await self._request("resources/read", params={"uri": uri})
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        result = resp.get("result")
        if not isinstance(result, dict):
            return {"text": "", "raw": result}
        content = result.get("content")
        text_parts: list[str] = []
        content_list: list[dict[str, Any]] = []
        if isinstance(content, list):
            content_list = [c for c in content if isinstance(c, dict)]
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    t = item.get("text")
                    if isinstance(t, str):
                        text_parts.append(t)
        return {"text": "".join(text_parts), "content": content_list, "raw": result}
