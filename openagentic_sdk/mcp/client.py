from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


def _encode_message(obj: Mapping[str, Any]) -> bytes:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


async def _read_message(stream: asyncio.StreamReader) -> Mapping[str, Any]:
    headers: dict[str, str] = {}
    while True:
        line = await stream.readline()
        if not line:
            raise EOFError("mcp: EOF")
        if line in (b"\r\n", b"\n"):
            break
        try:
            k, v = line.decode("utf-8", errors="replace").split(":", 1)
            headers[k.strip().lower()] = v.strip()
        except ValueError:
            continue
    n = int(headers.get("content-length", "0") or "0")
    if n <= 0:
        raise ValueError("mcp: missing Content-Length")
    body = await stream.readexactly(n)
    obj = json.loads(body.decode("utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError("mcp: message must be object")
    return obj


@dataclass
class StdioMcpClient:
    command: list[str]
    environment: Mapping[str, str] | None = None
    cwd: str | None = None

    _proc: asyncio.subprocess.Process | None = None
    _reader: asyncio.StreamReader | None = None
    _writer: asyncio.StreamWriter | None = None
    _stderr: asyncio.StreamReader | None = None
    _next_id: int = 1

    async def start(self) -> None:
        if self._proc is not None:
            return
        env = dict(os.environ)
        if self.environment:
            env.update({str(k): str(v) for k, v in dict(self.environment).items()})
        proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
            env=env,
        )
        if proc.stdin is None or proc.stdout is None:
            raise RuntimeError("mcp: subprocess pipes not available")

        # asyncio subprocess API already exposes StreamReader/StreamWriter.
        self._proc = proc
        self._reader = proc.stdout
        self._writer = proc.stdin
        self._stderr = proc.stderr

    async def close(self) -> None:
        proc = self._proc
        if proc is None:
            return
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        self._proc = None

    async def _request(self, method: str, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        await self.start()
        assert self._reader is not None and self._writer is not None
        rid = self._next_id
        self._next_id += 1
        msg = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            msg["params"] = dict(params)
        self._writer.write(_encode_message(msg))
        await self._writer.drain()

        while True:
            try:
                resp = await _read_message(self._reader)
            except EOFError:
                err = ""
                if self._stderr is not None:
                    try:
                        data = await asyncio.wait_for(self._stderr.read(), timeout=0.2)
                        err = data.decode("utf-8", errors="replace")
                    except Exception:  # noqa: BLE001
                        err = ""
                raise EOFError(f"mcp: EOF while waiting for {method}; stderr={err!r}")
            if resp.get("id") == rid:
                return resp

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
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    t = item.get("text")
                    if isinstance(t, str):
                        text_parts.append(t)
        return {"text": "".join(text_parts), "raw": result}

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
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    t = item.get("text")
                    if isinstance(t, str):
                        text_parts.append(t)
        return {"text": "".join(text_parts), "raw": result}

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
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    t = item.get("text")
                    if isinstance(t, str):
                        text_parts.append(t)
        return {"text": "".join(text_parts), "raw": result}
