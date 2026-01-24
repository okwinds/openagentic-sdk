import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk import query
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
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
        else:
            if method == "prompts/list":
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

        raw = json.dumps(resp, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):  # noqa: ANN001
        return


class LegacyProviderCallsRemoteMcpTool:
    name = "legacy-mcp-remote"

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


class TestMcpRemoteTools(unittest.IsolatedAsyncioTestCase):
    async def test_registers_and_invokes_remote_mcp_tools(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)

            httpd = HTTPServer(("127.0.0.1", 0), _Handler)
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
                    mcp_servers={"r": {"type": "remote", "url": f"http://127.0.0.1:{port}/rpc"}},
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
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
