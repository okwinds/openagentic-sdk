from __future__ import annotations

import json
import queue
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk import query
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class _SseServer:
    def __init__(self) -> None:
        self.stop = threading.Event()
        self.events: "queue.Queue[bytes]" = queue.Queue()

    def enqueue(self, obj: dict) -> None:
        data = json.dumps(obj, ensure_ascii=False)
        payload = f"data: {data}\n\n".encode("utf-8")
        self.events.put(payload)


class _Handler(BaseHTTPRequestHandler):
    server_version = "MCPStub/1"

    def do_GET(self):  # noqa: N802
        state: _SseServer = self.server.state  # type: ignore[attr-defined]
        if self.path.rstrip("/") != "/mcp/sse":
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        # Keep the connection open until shutdown; write events from this handler thread.
        while not state.stop.is_set():
            try:
                payload = state.events.get(timeout=0.1)
                self.wfile.write(payload)
                self.wfile.flush()
            except queue.Empty:
                continue
            except Exception:  # noqa: BLE001
                break

    def do_POST(self):  # noqa: N802
        state: _SseServer = self.server.state  # type: ignore[attr-defined]
        if self.path.rstrip("/") == "/mcp":
            # Make StreamableHTTP attempt fail, so RemoteMcpClient falls back to SSE.
            length = int(self.headers.get("Content-Length") or "0")
            if length:
                _ = self.rfile.read(length)
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path.rstrip("/") != "/mcp/message":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(length)
        req = json.loads(body.decode("utf-8", errors="replace"))
        rid = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}

        if method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "tools": [
                        {
                            "name": "echo",
                            "description": "echo",
                            "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
                        }
                    ]
                },
            }
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            if name == "echo":
                resp = {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": args.get("text", "")}]}}
            else:
                resp = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "unknown tool"}}
        elif method == "prompts/list":
            resp = {"jsonrpc": "2.0", "id": rid, "result": {"prompts": [{"name": "greet", "description": "greet"}]}}
        elif method == "prompts/get":
            name = params.get("name")
            if name == "greet":
                resp = {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": "hello"}]}}
            else:
                resp = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "unknown prompt"}}
        elif method == "resources/list":
            resp = {"jsonrpc": "2.0", "id": rid, "result": {"resources": [{"uri": "r1", "description": "res"}]}}
        elif method == "resources/read":
            uri = params.get("uri")
            if uri == "r1":
                resp = {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": "data"}]}}
            else:
                resp = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "unknown resource"}}
        else:
            resp = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "unknown method"}}

        # Respond to POST quickly; deliver the JSON-RPC response via SSE.
        self.send_response(202)
        self.send_header("Content-Length", "0")
        self.end_headers()
        state.enqueue(resp)

    def log_message(self, fmt, *args):  # noqa: ANN001
        return


class _DaemonThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True


class LegacyProviderCallsRemoteMcpTool:
    name = "legacy-mcp-remote-sse"

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, *, model: str, messages, tools=(), api_key=None):
        self.calls += 1
        if self.calls == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[
                    ToolCall(tool_use_id="m1", name="mcp__r__echo", arguments={"text": "hi"}),
                    ToolCall(tool_use_id="m2", name="mcp__r__prompt__greet", arguments={}),
                    ToolCall(tool_use_id="m3", name="mcp__r__resource__r1", arguments={}),
                ],
                usage={"total_tokens": 1},
                raw=None,
            )
        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 2}, raw=None)


class TestMcpRemoteSseTools(unittest.IsolatedAsyncioTestCase):
    async def test_registers_and_invokes_remote_mcp_tools_over_sse(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            state = _SseServer()

            httpd = _DaemonThreadingHTTPServer(("127.0.0.1", 0), _Handler)
            httpd.state = state  # type: ignore[attr-defined]
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            try:
                provider = LegacyProviderCallsRemoteMcpTool()
                options = OpenAgenticOptions(
                    provider=provider,
                    model="fake",
                    api_key="x",
                    cwd=str(root),
                    project_dir=str(root),
                    session_store=store,
                    permission_gate=PermissionGate(permission_mode="bypass"),
                    mcp_servers={"r": {"type": "remote", "url": f"http://127.0.0.1:{port}/mcp"}},
                )

                events = []
                async for e in query(prompt="hi", options=options):
                    events.append(e)

                tool_results = [e for e in events if getattr(e, "type", "") == "tool.result"]
                self.assertTrue(tool_results)
                outs = [getattr(tr, "output", None) for tr in tool_results]
                texts = [o.get("text") for o in outs if isinstance(o, dict)]
                self.assertIn("hi", texts)
                self.assertIn("hello", texts)
                self.assertIn("data", texts)
            finally:
                state.stop.set()
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
