import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import AgentDefinition, OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class TaskProvider:
    name = "fake"

    def __init__(self):
        self.calls = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self.calls += 1
        if self.calls == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall("t1", "Task", {"agent": "worker", "prompt": "x"})],
            )
        if any(m.get("role") == "tool" for m in messages):
            return ModelOutput(assistant_text="done", tool_calls=[])
        return ModelOutput(assistant_text="child", tool_calls=[])


class TestSessionLink(unittest.IsolatedAsyncioTestCase):
    async def test_child_meta_contains_parent(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgenticOptions(
                provider=TaskProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
                agents={"worker": AgentDefinition(description="d", prompt="child", tools=())},
            )
            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="parent", options=options):
                events.append(e)
            tr = next(
                e
                for e in events
                if getattr(e, "type", None) == "tool.result" and getattr(e, "tool_use_id", None) == "t1"
            )
            child_sid = tr.output["child_session_id"]
            meta = json.loads((root / "sessions" / child_sid / "meta.json").read_text(encoding="utf-8"))
            self.assertIn("parent_session_id", meta["metadata"])
            self.assertIn("parent_tool_use_id", meta["metadata"])
            self.assertEqual(meta["metadata"]["agent_name"], "worker")


if __name__ == "__main__":
    unittest.main()

