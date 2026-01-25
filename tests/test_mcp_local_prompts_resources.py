import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk import query
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class LegacyProviderCallsLocalMcpPrompt:
    name = "legacy-mcp-local-prompt"

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, *, model: str, messages, tools=(), api_key=None):
        _ = (model, messages, tools, api_key)
        self.calls += 1
        if self.calls == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall(tool_use_id="m1", name="mcp__test__prompt__hello", arguments={"name": "world"})],
                usage={"total_tokens": 1},
                raw=None,
            )
        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 2}, raw=None)


class LegacyProviderCallsLocalMcpResource:
    name = "legacy-mcp-local-resource"

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, *, model: str, messages, tools=(), api_key=None):
        _ = (model, messages, tools, api_key)
        self.calls += 1
        if self.calls == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall(tool_use_id="m1", name="mcp__test__resource__mem___txt", arguments={})],
                usage={"total_tokens": 1},
                raw=None,
            )
        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 2}, raw=None)


MCP_SERVER = """\
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
        write_message({"jsonrpc": "2.0", "id": mid, "result": {"tools": []}})
        continue
    if method == "prompts/list":
        write_message({"jsonrpc": "2.0", "id": mid, "result": {"prompts": [{"name": "hello", "description": "hello prompt", "arguments": [{"name": "name", "description": "Name"}]}]}})
        continue
    if method == "prompts/get":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "hello":
            write_message({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": f"hello {args.get('name','')}"}]}})
        else:
            write_message({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "unknown prompt"}})
        continue
    if method == "resources/list":
        write_message({"jsonrpc": "2.0", "id": mid, "result": {"resources": [{"uri": "mem://txt", "name": "mem.txt", "mimeType": "text/plain"}]}})
        continue
    if method == "resources/read":
        uri = params.get("uri")
        if uri == "mem://txt":
            write_message({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": "ok"}]}})
        else:
            write_message({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "unknown resource"}})
        continue
    write_message({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "unknown method"}})
"""


class TestMcpLocalPromptsResources(unittest.IsolatedAsyncioTestCase):
    async def test_registers_and_invokes_local_mcp_prompt(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            server = root / "mcp_server.py"
            server.write_text(MCP_SERVER, encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            provider = LegacyProviderCallsLocalMcpPrompt()
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

            tool_results = [e for e in events if getattr(e, "type", "") == "tool.result"]
            self.assertTrue(tool_results)
            out = getattr(tool_results[-1], "output", None)
            self.assertIsInstance(out, dict)
            self.assertEqual(out.get("text"), "hello world")

    async def test_registers_and_invokes_local_mcp_resource(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            server = root / "mcp_server.py"
            server.write_text(MCP_SERVER, encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            provider = LegacyProviderCallsLocalMcpResource()
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

            tool_results = [e for e in events if getattr(e, "type", "") == "tool.result"]
            self.assertTrue(tool_results)
            out = getattr(tool_results[-1], "output", None)
            self.assertIsInstance(out, dict)
            self.assertEqual(out.get("text"), "ok")


if __name__ == "__main__":
    unittest.main()
