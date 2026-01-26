from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import urllib.error

from .auth_store import McpAuthStore

from .http_client import HttpMcpClient
from .sse_client import SseMcpClient


@dataclass
class RemoteMcpClient:
    """Try StreamableHTTP first, then SSE."""

    url: str
    headers: Mapping[str, str] | None = None
    server_key: str | None = None

    _streamable: HttpMcpClient | None = None
    _sse: SseMcpClient | None = None

    def __post_init__(self) -> None:
        # If we have OpenCode-style OAuth tokens on disk, inject them unless the
        # caller already set Authorization.
        if not self.server_key:
            return
        hdrs = {str(k): str(v) for k, v in (self.headers or {}).items()}
        if "authorization" in {k.lower() for k in hdrs.keys()}:
            self.headers = hdrs
            return

        store = McpAuthStore.load_default()
        entry = store.get_for_url(self.server_key, server_url=self.url)
        if entry is not None and entry.tokens is not None and entry.tokens.access_token:
            hdrs["Authorization"] = f"Bearer {entry.tokens.access_token}"
        self.headers = hdrs

    async def close(self) -> None:
        if self._sse is not None:
            await self._sse.close()

    async def _client(self) -> Any:
        if self._streamable is not None:
            return self._streamable
        if self._sse is not None:
            return self._sse

        # Attempt StreamableHTTP (simple POST JSON) first.
        # Keep probe timeout low so we don't stall startup when the server only
        # supports SSE.
        streamable = HttpMcpClient(url=self.url, headers=self.headers, timeout_s=1.0)
        try:
            await streamable.list_tools()
            self._streamable = streamable
            return streamable
        except urllib.error.HTTPError as e:
            # Treat auth errors as a signal that StreamableHTTP is supported.
            if int(getattr(e, "code", 0) or 0) in (401, 403):
                self._streamable = streamable
                return streamable
            # Other HTTP errors: fall back to SSE.
        except Exception:  # noqa: BLE001
            pass

        # Fall back to SSE transport.
        sse = SseMcpClient(base_url=self.url, headers=self.headers)
        await sse.start()
        self._sse = sse
        return sse

    async def list_tools(self) -> list[dict[str, Any]]:
        c = await self._client()
        return await c.list_tools()

    async def call_tool(self, *, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        c = await self._client()
        return await c.call_tool(name=name, arguments=arguments)

    async def list_prompts(self) -> list[dict[str, Any]]:
        c = await self._client()
        return await c.list_prompts()

    async def get_prompt(self, *, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        c = await self._client()
        return await c.get_prompt(name=name, arguments=arguments)

    async def list_resources(self) -> list[dict[str, Any]]:
        c = await self._client()
        return await c.list_resources()

    async def read_resource(self, *, uri: str) -> dict[str, Any]:
        c = await self._client()
        return await c.read_resource(uri=uri)
