from __future__ import annotations

import json
import sys


def _encode(obj: dict) -> bytes:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def _read_message() -> dict:
    # Read headers.
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            raise EOFError
        if line in (b"\r\n", b"\n"):
            break
        try:
            k, v = line.decode("utf-8", errors="replace").split(":", 1)
            headers[k.strip().lower()] = v.strip()
        except ValueError:
            continue
    n = int(headers.get("content-length", "0") or "0")
    if n <= 0:
        raise ValueError("missing Content-Length")
    body = sys.stdin.buffer.read(n)
    obj = json.loads(body.decode("utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError("message must be object")
    return obj


def _send(obj: dict) -> None:
    sys.stdout.buffer.write(_encode(obj))
    sys.stdout.buffer.flush()


def main() -> int:
    opened: dict[str, str] = {}
    while True:
        try:
            msg = _read_message()
        except EOFError:
            return 0

        method = msg.get("method")
        rid = msg.get("id")

        def respond(result: object) -> None:
            if isinstance(rid, int):
                _send({"jsonrpc": "2.0", "id": rid, "result": result})

        def respond_error(code: int, message: str) -> None:
            if isinstance(rid, int):
                _send({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})

        if method == "initialize":
            respond(
                {
                    "capabilities": {
                        "hoverProvider": True,
                        "definitionProvider": True,
                        "referencesProvider": True,
                        "documentSymbolProvider": True,
                        "workspaceSymbolProvider": True,
                        "implementationProvider": True,
                        "callHierarchyProvider": True,
                    }
                }
            )
            continue

        if method == "initialized":
            # Notification.
            continue

        if method == "textDocument/didOpen":
            params = msg.get("params")
            if isinstance(params, dict):
                td = params.get("textDocument")
                if isinstance(td, dict):
                    uri = td.get("uri")
                    text = td.get("text")
                    if isinstance(uri, str) and isinstance(text, str):
                        opened[uri] = text
                        # Publish a single fake diagnostic.
                        _send(
                            {
                                "jsonrpc": "2.0",
                                "method": "textDocument/publishDiagnostics",
                                "params": {
                                    "uri": uri,
                                    "diagnostics": [
                                        {
                                            "range": {
                                                "start": {"line": 0, "character": 0},
                                                "end": {"line": 0, "character": 1},
                                            },
                                            "severity": 1,
                                            "source": "stub-lsp",
                                            "message": "stub diagnostic",
                                        }
                                    ],
                                },
                            }
                        )
            continue

        # Helpers for location-ish responses.
        def location(uri: str) -> dict:
            return {
                "uri": uri,
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
            }

        if method == "textDocument/hover":
            params = msg.get("params")
            uri = ""
            if isinstance(params, dict):
                td = params.get("textDocument")
                if isinstance(td, dict) and isinstance(td.get("uri"), str):
                    uri = td["uri"]
            if uri and uri in opened:
                respond({"contents": {"kind": "markdown", "value": "stub hover"}})
            else:
                respond(None)
            continue

        if method == "textDocument/definition":
            params = msg.get("params")
            uri = ""
            if isinstance(params, dict):
                td = params.get("textDocument")
                if isinstance(td, dict) and isinstance(td.get("uri"), str):
                    uri = td["uri"]
            respond([location(uri)] if uri else [])
            continue

        if method == "textDocument/references":
            params = msg.get("params")
            uri = ""
            if isinstance(params, dict):
                td = params.get("textDocument")
                if isinstance(td, dict) and isinstance(td.get("uri"), str):
                    uri = td["uri"]
            respond([location(uri)] if uri else [])
            continue

        if method == "textDocument/documentSymbol":
            params = msg.get("params")
            uri = ""
            if isinstance(params, dict):
                td = params.get("textDocument")
                if isinstance(td, dict) and isinstance(td.get("uri"), str):
                    uri = td["uri"]
            respond(
                [
                    {
                        "name": "StubSymbol",
                        "kind": 12,
                        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
                        "selectionRange": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
                    }
                ]
                if uri
                else []
            )
            continue

        if method == "workspace/symbol":
            respond(
                [
                    {
                        "name": "StubWorkspaceSymbol",
                        "kind": 12,
                        "location": {"uri": "file:///stub", "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}}},
                    }
                ]
            )
            continue

        if method == "textDocument/implementation":
            params = msg.get("params")
            uri = ""
            if isinstance(params, dict):
                td = params.get("textDocument")
                if isinstance(td, dict) and isinstance(td.get("uri"), str):
                    uri = td["uri"]
            respond([location(uri)] if uri else [])
            continue

        if method == "textDocument/prepareCallHierarchy":
            params = msg.get("params")
            uri = ""
            if isinstance(params, dict):
                td = params.get("textDocument")
                if isinstance(td, dict) and isinstance(td.get("uri"), str):
                    uri = td["uri"]
            respond(
                [
                    {
                        "name": "StubCall",
                        "kind": 12,
                        "uri": uri or "file:///stub",
                        "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
                        "selectionRange": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
                    }
                ]
                if uri
                else []
            )
            continue

        if method == "callHierarchy/incomingCalls" or method == "callHierarchy/outgoingCalls":
            respond([])
            continue

        if isinstance(rid, int):
            respond_error(-32601, f"Method not found: {method}")
        # Else ignore notifications.


if __name__ == "__main__":
    raise SystemExit(main())
