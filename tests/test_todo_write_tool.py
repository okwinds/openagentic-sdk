import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.options import OpenAgentOptions
from open_agent_sdk.permissions.gate import PermissionGate
from open_agent_sdk.providers.base import ModelOutput, ToolCall
from open_agent_sdk.sessions.store import FileSessionStore
from open_agent_sdk.tools.defaults import default_tool_registry


class TodoProvider:
    name = "fake"

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, messages, tools, api_key)
        if not any(m.get("role") == "tool" for m in messages):
            return ModelOutput(
                assistant_text=None,
                tool_calls=[
                    ToolCall(
                        tool_use_id="call_1",
                        name="TodoWrite",
                        arguments={
                            "todos": [
                                {"content": "A", "activeForm": "Doing A", "status": "in_progress"},
                                {"content": "B", "activeForm": "Do B", "status": "pending"},
                            ]
                        },
                    )
                ],
            )
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestTodoWriteTool(unittest.IsolatedAsyncioTestCase):
    async def test_default_registry_includes_todowrite(self) -> None:
        names = default_tool_registry().names()
        self.assertIn("TodoWrite", names)

    async def test_runtime_persists_todos_json(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgentOptions(
                provider=TodoProvider(),
                model="fake",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                tools=default_tool_registry(),
                allowed_tools=["TodoWrite"],
            )
            import open_agent_sdk

            events = []
            async for e in open_agent_sdk.query(prompt="todo", options=options):
                events.append(e)

            session_id = next((e.session_id for e in events if getattr(e, "type", "") == "system.init"), "")
            self.assertTrue(session_id)

            todo_file = store.session_dir(session_id) / "todos.json"
            self.assertTrue(todo_file.exists())
            data = json.loads(todo_file.read_text(encoding="utf-8"))
            self.assertEqual(len(data.get("todos") or []), 2)


if __name__ == "__main__":
    unittest.main()

