from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .client import StdioLspClient
from .config import LspServerConfig, parse_lsp_config
from .registry import LspServerDefinition, build_server_registry


def _normalize_ext(ext: str) -> str:
    if not ext:
        return ""
    return ext if ext.startswith(".") else f".{ext}"


@dataclass
class LspManager:
    cfg: dict[str, Any] | None
    project_root: str

    _clients: dict[str, StdioLspClient] = field(default_factory=dict)
    _broken: set[str] = field(default_factory=set)
    _spawning: dict[str, asyncio.Future[StdioLspClient | None]] = field(default_factory=dict)
    _client_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _servers: dict[str, LspServerDefinition] = field(default_factory=dict)
    _enabled: bool = True

    async def __aenter__(self) -> "LspManager":
        # Validate config shape (parity with OpenCode schema constraints).
        _ = parse_lsp_config(self.cfg)

        enabled, servers = build_server_registry(cfg=self.cfg or {}, workspace_dir=Path(self.project_root))
        self._enabled = enabled
        self._servers = servers
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
        self._broken.clear()
        self._spawning.clear()

    def _file_key(self, file_path: str) -> str:
        p = Path(file_path)
        # OpenCode maps by extension, but includes Dockerfile-like names.
        return p.suffix or p.name

    def _matching_servers(self, file_path: str) -> list[LspServerDefinition]:
        if not self._enabled:
            return []
        key = self._file_key(file_path)
        out: list[LspServerDefinition] = []
        for s in self._servers.values():
            exts = s.extensions
            if exts and key not in exts:
                continue
            out.append(s)
        return out

    async def _get_or_spawn(self, server: LspServerDefinition, *, root: str) -> StdioLspClient | None:
        key = f"{root}\0{server.server_id}"
        if key in self._broken:
            return None

        async with self._client_lock:
            existing = self._clients.get(key)
            if existing is not None:
                return existing
            inflight = self._spawning.get(key)
            if inflight is not None:
                # Another coroutine is already spawning; wait outside lock.
                pass
            else:
                fut: asyncio.Future[StdioLspClient | None] = asyncio.get_running_loop().create_future()
                self._spawning[key] = fut
                inflight = fut

                async def _spawn() -> None:
                    try:
                        if not server.command:
                            fut.set_result(None)
                            return
                        c = StdioLspClient(
                            command=list(server.command),
                            cwd=str(root),
                            environment=server.env,
                            initialization_options=server.initialization,
                            server_id=server.server_id,
                        )
                        await c.ensure_initialized(root_path=str(root))
                        async with self._client_lock:
                            self._clients[key] = c
                        fut.set_result(c)
                    except Exception:
                        self._broken.add(key)
                        try:
                            fut.set_result(None)
                        except Exception:  # noqa: BLE001
                            pass
                    finally:
                        async with self._client_lock:
                            self._spawning.pop(key, None)

                asyncio.create_task(_spawn())

        assert inflight is not None
        return await inflight

    async def clients_for_file(self, file_path: str) -> list[tuple[StdioLspClient, LspServerDefinition]]:
        out: list[tuple[StdioLspClient, LspServerDefinition]] = []
        for s in self._matching_servers(file_path):
            try:
                root = s.root(file_path)
            except Exception:
                root = None
            if not root:
                continue
            c = await self._get_or_spawn(s, root=root)
            if c is None:
                continue
            out.append((c, s))
        return out

    async def client_for_file(self, file_path: str) -> tuple[StdioLspClient, LspServerConfig]:
        # Back-compat for existing tool wrapper: choose the first matching client.
        pairs = await self.clients_for_file(file_path)
        if not pairs:
            raise RuntimeError("No LSP server available for this file type.")
        c, s = pairs[0]
        return c, LspServerConfig(server_id=s.server_id, command=tuple(s.command or ()), extensions=tuple(s.extensions))

    async def touch(self, file_path: str, *, language_id: str | None = None) -> str:
        c, _ = await self.client_for_file(file_path)
        return await c.touch_file(file_path, language_id=language_id)

    async def has_clients(self, file_path: str) -> bool:
        """Best-effort check without spawning clients (OpenCode-like)."""

        for s in self._matching_servers(file_path):
            try:
                root = s.root(file_path)
            except Exception:
                root = None
            if not root:
                continue
            key = f"{root}\0{s.server_id}"
            if key in self._broken:
                continue
            return True
        return False

    async def touch_file(self, file_path: str, *, wait_for_diagnostics: bool = False) -> None:
        pairs = await self.clients_for_file(file_path)
        if not pairs:
            raise RuntimeError("No LSP server available for this file type.")

        # OpenCode parity: start waits before sending didOpen/didChange.
        waits: list[asyncio.Task[None]] = []
        if wait_for_diagnostics:
            for c, _ in pairs:
                waits.append(asyncio.create_task(c.wait_for_diagnostics(file_path=file_path)))
        await asyncio.gather(*[c.touch_file(file_path) for c, _ in pairs], return_exceptions=True)
        for t in waits:
            try:
                await t
            except Exception:  # noqa: BLE001
                pass

    async def op(self, *, operation: str, file_path: str, line0: int, character0: int) -> Any:
        pairs = await self.clients_for_file(file_path)
        if not pairs:
            raise RuntimeError("No LSP server available for this file type.")

        # OpenCode tool behavior: touch file and wait for diagnostics before op.
        await self.touch_file(file_path, wait_for_diagnostics=True)

        uri = Path(file_path).resolve().as_uri()

        async def per_client(c: StdioLspClient) -> Any:
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
                item0 = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else None
                if not isinstance(item0, dict):
                    return []
                if operation == "incomingCalls":
                    return await c.request_incoming_calls(item=item0)
                return await c.request_outgoing_calls(item=item0)
            raise ValueError(f"Unknown LSP operation: {operation}")

        results = await asyncio.gather(*[per_client(c) for c, _ in pairs], return_exceptions=True)

        # OpenCode merge rules.
        if operation == "hover":
            return [r if not isinstance(r, Exception) else None for r in results]

        # workspaceSymbol kind filter + top-10 per client.
        if operation == "workspaceSymbol":
            kinds = {5, 6, 11, 12, 13, 14, 23, 10}  # class, method, interface, function, variable, constant, struct, enum
            out: list[Any] = []
            for r in results:
                if isinstance(r, Exception) or r is None:
                    continue
                if isinstance(r, list):
                    filtered = [x for x in r if isinstance(x, dict) and isinstance(x.get("kind"), int) and x.get("kind") in kinds]
                    out.extend(filtered[:10])
            return out

        flat: list[Any] = []
        for r in results:
            if isinstance(r, Exception) or r is None:
                continue
            if isinstance(r, list):
                flat.extend([x for x in r if x])
            else:
                flat.append(r)
        return flat
        raise ValueError(f"Unknown LSP operation: {operation}")
