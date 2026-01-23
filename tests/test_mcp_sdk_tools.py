import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk import OpenAgentOptions, create_sdk_mcp_server, tool
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args):
    return {
        "content": [
            {
                "type": "text",
                "text": str(float(args["a"]) + float(args["b"])),
            }
        ]
    }


class FakeProvider:
    name = "fake"

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, tools, api_key)
        if not any(m.get("role") == "tool" for m in messages):
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall(tool_use_id="call_1", name="mcp__calc__add", arguments={"a": 1, "b": 2})],
            )
        tool_msg = next(m for m in messages if m.get("role") == "tool")
        out = json.loads(tool_msg.get("content") or "{}")
        text = ""
        if isinstance(out, dict):
            content = out.get("content") or []
            if isinstance(content, list) and content and isinstance(content[0], dict):
                text = str(content[0].get("text") or "")
        return ModelOutput(assistant_text=f"sum={text}", tool_calls=[])


class TestMcpSdkTools(unittest.IsolatedAsyncioTestCase):
    async def test_sdk_mcp_tool_runs(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            server = create_sdk_mcp_server(name="calculator", version="1.0.0", tools=[add])
            options = OpenAgentOptions(
                provider=FakeProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                allowed_tools=["mcp__calc__add"],
                mcp_servers={"calc": server},
            )
            import openagentic_sdk

            r = await openagentic_sdk.run(prompt="hi", options=options)
            self.assertEqual(r.final_text, "sum=3.0")


if __name__ == "__main__":
    unittest.main()

