from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .protocol import encode_message, read_message


def _file_uri(file_path: str) -> str:
    return Path(file_path).resolve().as_uri()


@dataclass
class StdioLspClient:
    command: list[str]
    cwd: str
    environment: Mapping[str, str] | None = None
    initialization_options: Mapping[str, Any] | None = None
    root_uri: str | None = None

    _proc: asyncio.subprocess.Process | None = None
    _reader: asyncio.StreamReader | None = None
    _writer: asyncio.StreamWriter | None = None
    _stderr: asyncio.StreamReader | None = None
    _next_id: int = 1
    _pending: dict[int, asyncio.Future[Mapping[str, Any]]] = field(default_factory=dict)
    _write_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _reader_task: asyncio.Task[None] | None = None
    _diagnostics_by_uri: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    _opened_versions: dict[str, int] = field(default_factory=dict)
    _initialized: bool = False

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
            raise RuntimeError("lsp: subprocess pipes not available")

        self._proc = proc
        self._reader = proc.stdout
        self._writer = proc.stdin
        self._stderr = proc.stderr
        self._reader_task = asyncio.create_task(self._reader_loop())

    async def close(self) -> None:
        # Cancel reader loop first to avoid hangs on shutdown.
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except BaseException:  # noqa: BLE001
                pass
            self._reader_task = None

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

    async def _reader_loop(self) -> None:
        assert self._reader is not None
        while True:
            msg = await read_message(self._reader)
            if "id" in msg:
                rid = msg.get("id")
                if isinstance(rid, int):
                    fut = self._pending.pop(rid, None)
                    if fut is not None and not fut.done():
                        fut.set_result(msg)
                continue
            method = msg.get("method")
            if method == "textDocument/publishDiagnostics":
                params = msg.get("params")
                if isinstance(params, dict):
                    uri = params.get("uri")
                    diags = params.get("diagnostics")
                    if isinstance(uri, str) and isinstance(diags, list):
                        self._diagnostics_by_uri[uri] = [d for d in diags if isinstance(d, dict)]
                continue
            # Ignore other notifications.

    async def _request(self, method: str, params: Mapping[str, Any] | None = None, *, timeout_s: float = 10.0) -> Mapping[str, Any]:
        await self.start()
        assert self._writer is not None

        rid = self._next_id
        self._next_id += 1
        fut: asyncio.Future[Mapping[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut

        msg: dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            msg["params"] = dict(params)
        async with self._write_lock:
            self._writer.write(encode_message(msg))
            await self._writer.drain()

        try:
            resp = await asyncio.wait_for(fut, timeout=timeout_s)
        except Exception:
            self._pending.pop(rid, None)
            raise
        return resp

    async def _notify(self, method: str, params: Mapping[str, Any] | None = None) -> None:
        await self.start()
        assert self._writer is not None
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = dict(params)
        async with self._write_lock:
            self._writer.write(encode_message(msg))
            await self._writer.drain()

    async def ensure_initialized(self, *, root_path: str, initialization_options: Mapping[str, Any] | None = None) -> None:
        if self._initialized:
            return
        self.root_uri = self.root_uri or Path(root_path).resolve().as_uri()

        init_opts = dict(self.initialization_options or {})
        if initialization_options:
            init_opts.update(dict(initialization_options))

        resp = await self._request(
            "initialize",
            params={
                "processId": None,
                "rootUri": self.root_uri,
                "capabilities": {},
                "initializationOptions": init_opts or None,
                "workspaceFolders": [{"uri": self.root_uri, "name": "workspace"}],
            },
            timeout_s=20.0,
        )
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(f"lsp: initialize failed: {resp.get('error')}")
        await self._notify("initialized", params={})
        self._initialized = True

    async def touch_file(self, file_path: str, *, language_id: str | None = None) -> str:
        """Open the file in the LSP server (didOpen).

        LSP servers generally require didOpen before navigation requests return data.
        """

        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(str(p))
        uri = _file_uri(str(p))
        text = p.read_text(encoding="utf-8", errors="replace")
        version = self._opened_versions.get(uri, 0) + 1
        self._opened_versions[uri] = version
        lang = language_id or (p.suffix.lstrip(".") or "plaintext")
        await self._notify(
            "textDocument/didOpen",
            params={
                "textDocument": {
                    "uri": uri,
                    "languageId": lang,
                    "version": version,
                    "text": text,
                }
            },
        )
        return uri

    def diagnostics(self) -> dict[str, list[dict[str, Any]]]:
        return dict(self._diagnostics_by_uri)

    async def request_hover(self, *, uri: str, line0: int, character0: int) -> Any:
        resp = await self._request(
            "textDocument/hover",
            params={"textDocument": {"uri": uri}, "position": {"line": line0, "character": character0}},
        )
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        return resp.get("result")

    async def request_definition(self, *, uri: str, line0: int, character0: int) -> Any:
        resp = await self._request(
            "textDocument/definition",
            params={"textDocument": {"uri": uri}, "position": {"line": line0, "character": character0}},
        )
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        return resp.get("result")

    async def request_references(self, *, uri: str, line0: int, character0: int) -> Any:
        resp = await self._request(
            "textDocument/references",
            params={
                "textDocument": {"uri": uri},
                "position": {"line": line0, "character": character0},
                "context": {"includeDeclaration": True},
            },
        )
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        return resp.get("result")

    async def request_document_symbol(self, *, uri: str) -> Any:
        resp = await self._request("textDocument/documentSymbol", params={"textDocument": {"uri": uri}})
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        return resp.get("result")

    async def request_workspace_symbol(self, *, query: str) -> Any:
        resp = await self._request("workspace/symbol", params={"query": query})
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        return resp.get("result")

    async def request_implementation(self, *, uri: str, line0: int, character0: int) -> Any:
        resp = await self._request(
            "textDocument/implementation",
            params={"textDocument": {"uri": uri}, "position": {"line": line0, "character": character0}},
        )
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        return resp.get("result")

    async def request_prepare_call_hierarchy(self, *, uri: str, line0: int, character0: int) -> Any:
        resp = await self._request(
            "textDocument/prepareCallHierarchy",
            params={"textDocument": {"uri": uri}, "position": {"line": line0, "character": character0}},
        )
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        return resp.get("result")

    async def request_incoming_calls(self, *, item: Mapping[str, Any]) -> Any:
        resp = await self._request("callHierarchy/incomingCalls", params={"item": dict(item)})
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        return resp.get("result")

    async def request_outgoing_calls(self, *, item: Mapping[str, Any]) -> Any:
        resp = await self._request("callHierarchy/outgoingCalls", params={"item": dict(item)})
        if isinstance(resp.get("error"), dict):
            raise RuntimeError(str(resp.get("error")))
        return resp.get("result")
