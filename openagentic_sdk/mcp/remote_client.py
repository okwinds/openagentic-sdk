from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .http_client import HttpMcpClient
from .sse_client import SseMcpClient


@dataclass
class RemoteMcpClient:
    """Try StreamableHTTP first, then SSE."""

    url: str
    headers: Mapping[str, str] | None = None

    _streamable: HttpMcpClient | None = None
    _sse: SseMcpClient | None = None

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
        except Exception:  # noqa: BLE001
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
