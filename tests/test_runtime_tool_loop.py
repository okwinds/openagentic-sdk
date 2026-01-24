import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.tools.read import ReadTool
from openagentic_sdk.tools.registry import ToolRegistry


class FakeProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls = []

    async def complete(
        self,
        *,
        model,
        input,
        tools=(),
        api_key=None,
        previous_response_id=None,
        store=True,
        include=(),
    ):
        self.calls.append({"model": model, "input": list(input), "previous_response_id": previous_response_id, "store": store})

        # First call: request a tool call
        if previous_response_id is None:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall(tool_use_id="call_1", name="Read", arguments={"file_path": "a.txt"})],
                usage={"total_tokens": 1},
                raw=None,
                response_id="resp_1",
            )

        # Second call: expect function_call_output input
        tool_item = next(i for i in input if isinstance(i, dict) and i.get("type") == "function_call_output")
        assert tool_item.get("call_id") == "call_1"
        data = json.loads(tool_item.get("output") or "{}")
        return ModelOutput(
            assistant_text=f"OK: {data.get('content','')}",
            tool_calls=[],
            usage={"total_tokens": 2},
            raw=None,
            response_id="resp_2",
        )


class TestRuntimeToolLoop(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_runs_tool_and_returns_result(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("hello", encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            tools = ToolRegistry([ReadTool()])
            provider = FakeProvider()
            options = OpenAgenticOptions(
                provider=provider,
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

            self.assertEqual(len(provider.calls), 2)
            self.assertIsNone(provider.calls[0]["previous_response_id"])
            self.assertEqual(provider.calls[1]["previous_response_id"], "resp_1")

            types = [e.type for e in events]
            self.assertIn("tool.use", types)
            self.assertIn("tool.result", types)
            self.assertIn("result", types)


if __name__ == "__main__":
    unittest.main()
