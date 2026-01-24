import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk import query
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class LegacyProviderCallsMcpTool:
    name = "legacy-mcp"

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, *, model: str, messages, tools=(), api_key=None):
        self.calls += 1
        if self.calls == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall(tool_use_id="m1", name="mcp__test__echo", arguments={"text": "hi"})],
                usage={"total_tokens": 1},
                raw=None,
            )
        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 2}, raw=None)


class TestMcpLocalTools(unittest.IsolatedAsyncioTestCase):
    async def test_registers_and_invokes_local_mcp_tools(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            # Minimal MCP stdio server (LSP-style framing).
            server = root / "mcp_server.py"
            server.write_text(
                """\
import json
import sys


def read_message():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\\r\\n", b"\\n"):
            break
        k, v = line.decode("utf-8", errors="replace").split(":", 1)
        headers[k.strip().lower()] = v.strip()
    n = int(headers.get("content-length", "0"))
    if n <= 0:
        return None
    body = sys.stdin.buffer.read(n)
    return json.loads(body.decode("utf-8", errors="replace"))


def write_message(obj):
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(raw)}\\r\\n\\r\\n".encode("ascii"))
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


while True:
    msg = read_message()
    if msg is None:
        break
    mid = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}
    if method == "tools/list":
        write_message({"jsonrpc": "2.0", "id": mid, "result": {"tools": [{"name": "echo", "description": "echo", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}]}})
        continue
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "echo":
            write_message({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": args.get("text", "")}]}})
        else:
            write_message({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "unknown tool"}})
        continue
    write_message({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "unknown method"}})
""",
                encoding="utf-8",
            )

            store = FileSessionStore(root_dir=root)
            provider = LegacyProviderCallsMcpTool()
            options = OpenAgenticOptions(
                provider=provider,
                model="fake",
                api_key="x",
                cwd=str(root),
                project_dir=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                mcp_servers={
                    "test": {
                        "type": "local",
                        "command": [sys.executable, str(server)],
                        "environment": {},
                    }
                },
            )

            events = []
            async for e in query(prompt="hi", options=options):
                events.append(e)

            # Verify the MCP tool call produced a ToolResult with echoed output.
            tool_results = [e for e in events if getattr(e, "type", "") == "tool.result"]
            self.assertTrue(tool_results)
            last = tool_results[-1]
            out = getattr(last, "output", None)
            self.assertIsInstance(out, dict)
            self.assertEqual(out.get("text"), "hi")


if __name__ == "__main__":
    unittest.main()
