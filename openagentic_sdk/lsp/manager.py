from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .client import StdioLspClient
from .config import LspConfig, LspServerConfig


def _normalize_ext(ext: str) -> str:
    if not ext:
        return ""
    return ext if ext.startswith(".") else f".{ext}"


@dataclass
class LspManager:
    config: LspConfig
    project_root: str

    _clients: dict[str, StdioLspClient] = field(default_factory=dict)
    _client_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def __aenter__(self) -> "LspManager":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        await self.close()

    async def close(self) -> None:
        for c in list(self._clients.values()):
            try:
                await c.close()
            except Exception:  # noqa: BLE001
                pass
        self._clients.clear()

    def _select_server(self, file_path: str) -> LspServerConfig | None:
        if not self.config.enabled:
            return None
        p = Path(file_path)
        ext = p.suffix.lower()
        for s in self.config.servers:
            if s.disabled:
                continue
            if s.extensions:
                norm_exts = {_normalize_ext(e).lower() for e in s.extensions}
                if ext in norm_exts:
                    return s
        return None

    async def client_for_file(self, file_path: str) -> tuple[StdioLspClient, LspServerConfig]:
        server = self._select_server(file_path)
        if server is None:
            raise RuntimeError("No LSP server available for this file type.")

        async with self._client_lock:
            c = self._clients.get(server.server_id)
            if c is None:
                c = StdioLspClient(
                    command=list(server.command),
                    cwd=str(self.project_root),
                    environment=server.env,
                    initialization_options=server.initialization,
                )
                self._clients[server.server_id] = c
        await c.ensure_initialized(root_path=str(self.project_root))
        return c, server

    async def touch(self, file_path: str, *, language_id: str | None = None) -> str:
        c, _ = await self.client_for_file(file_path)
        return await c.touch_file(file_path, language_id=language_id)

    async def op(self, *, operation: str, file_path: str, line0: int, character0: int) -> Any:
        c, _ = await self.client_for_file(file_path)
        uri = await c.touch_file(file_path)

        if operation == "goToDefinition":
            return await c.request_definition(uri=uri, line0=line0, character0=character0)
        if operation == "findReferences":
            return await c.request_references(uri=uri, line0=line0, character0=character0)
        if operation == "hover":
            return await c.request_hover(uri=uri, line0=line0, character0=character0)
        if operation == "documentSymbol":
            return await c.request_document_symbol(uri=uri)
        if operation == "workspaceSymbol":
            return await c.request_workspace_symbol(query="")
        if operation == "goToImplementation":
            return await c.request_implementation(uri=uri, line0=line0, character0=character0)
        if operation == "prepareCallHierarchy":
            return await c.request_prepare_call_hierarchy(uri=uri, line0=line0, character0=character0)
        if operation in ("incomingCalls", "outgoingCalls"):
            items = await c.request_prepare_call_hierarchy(uri=uri, line0=line0, character0=character0)
            if not items:
                return []
            item0 = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else None
            if not isinstance(item0, dict):
                return []
            if operation == "incomingCalls":
                return await c.request_incoming_calls(item=item0)
            return await c.request_outgoing_calls(item=item0)
        raise ValueError(f"Unknown LSP operation: {operation}")
