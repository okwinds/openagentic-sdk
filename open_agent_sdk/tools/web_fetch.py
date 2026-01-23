from __future__ import annotations

import ipaddress
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from .base import Tool, ToolContext


FetchTransport = Callable[[str, Mapping[str, str]], tuple[int, Mapping[str, str], bytes]]


def _default_fetch_transport(url: str, headers: Mapping[str, str]) -> tuple[int, Mapping[str, str], bytes]:
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as resp:
        status = int(getattr(resp, "status", 200))
        resp_headers = {k.lower(): v for k, v in dict(resp.headers).items()}
        body = resp.read()
    return status, resp_headers, body


def _is_blocked_host(host: str) -> bool:
    host_lower = host.lower()
    if host_lower in ("localhost",):
        return True
    if host_lower.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


@dataclass(frozen=True, slots=True)
class WebFetchTool(Tool):
    name: str = "WebFetch"
    description: str = "Fetch a URL over HTTP(S)."
    max_bytes: int = 1024 * 1024
    allow_private_networks: bool = False
    transport: FetchTransport = _default_fetch_transport

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        url = tool_input.get("url")
        if not isinstance(url, str) or not url:
            raise ValueError("WebFetch: 'url' must be a non-empty string")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("WebFetch: only http/https URLs are allowed")
        if not parsed.hostname:
            raise ValueError("WebFetch: URL must include a hostname")
        if not self.allow_private_networks and _is_blocked_host(parsed.hostname):
            raise ValueError("WebFetch: blocked hostname")

        headers = tool_input.get("headers") or {}
        if not isinstance(headers, dict):
            raise ValueError("WebFetch: 'headers' must be an object")

        status, resp_headers, body = self.transport(url, {str(k): str(v) for k, v in headers.items()})
        if len(body) > self.max_bytes:
            body = body[: self.max_bytes]

        content_type = resp_headers.get("content-type")
        text = body.decode("utf-8", errors="replace")
        return {"url": url, "status": status, "content_type": content_type, "text": text}

