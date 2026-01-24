from __future__ import annotations

import asyncio
import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


def _post_json(url: str, payload: Mapping[str, Any], headers: Mapping[str, str] | None, *, timeout_s: float) -> Mapping[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(str(k), str(v))
    with urllib.request.urlopen(req, timeout=float(timeout_s)) as resp:
        body = resp.read()
    obj = json.loads(body.decode("utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError("mcp http: response must be object")
    return obj


@dataclass
class HttpMcpClient:
    url: str
    headers: Mapping[str, str] | None = None
    timeout_s: float = 10.0
    _next_id: int = 1

    async def _request(self, method: str, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        rid = self._next_id
        self._next_id += 1
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            payload["params"] = dict(params)
        return await asyncio.to_thread(_post_json, self.url, payload, self.headers, timeout_s=self.timeout_s)

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
