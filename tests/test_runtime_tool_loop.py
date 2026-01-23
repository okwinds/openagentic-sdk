import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgentOptions
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.tools.read import ReadTool
from openagentic_sdk.tools.registry import ToolRegistry
from openagentic_sdk.permissions.gate import PermissionGate


class FakeProvider:
    name = "fake"

    async def complete(self, *, model, messages, tools=(), api_key=None):
        # If we have no tool result yet, request a Read tool call
        if not any(m.get("role") == "tool" for m in messages):
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall(tool_use_id="call_1", name="Read", arguments={"file_path": "a.txt"})],
                usage={"total_tokens": 1},
                raw=None,
            )
        # Otherwise, respond with a message that includes the tool output
        tool_msg = next(m for m in messages if m.get("role") == "tool")
        data = json.loads(tool_msg.get("content") or "{}")
        return ModelOutput(
            assistant_text=f"OK: {data.get('content','')}",
            tool_calls=[],
            usage={"total_tokens": 2},
            raw=None,
        )


class TestRuntimeToolLoop(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_runs_tool_and_returns_result(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("hello", encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            tools = ToolRegistry([ReadTool()])
            options = OpenAgentOptions(
                provider=FakeProvider(),
                model="fake",
                api_key="x",
                cwd=str(root),
                tools=tools,
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
            )

            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="read file", options=options):
                events.append(e)

            types = [e.type for e in events]
            self.assertIn("tool.use", types)
            self.assertIn("tool.result", types)
            self.assertIn("result", types)


if __name__ == "__main__":
    unittest.main()

