import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.tools.defaults import default_tool_registry


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


class OpenCodeTodoProvider:
    name = "fake"

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, tools, api_key)
        if not any(m.get("role") == "tool" for m in messages):
            return ModelOutput(
                assistant_text=None,
                tool_calls=[
                    ToolCall(
                        tool_use_id="call_1",
                        name="TodoWrite",
                        arguments={
                            "todos": [
                                {"content": "A", "status": "in_progress", "priority": "high", "id": "t1"},
                                {"content": "B", "status": "cancelled", "priority": "low", "id": "t2"},
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
            options = OpenAgenticOptions(
                provider=TodoProvider(),
                model="fake",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                tools=default_tool_registry(),
                allowed_tools=["TodoWrite"],
            )
            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="todo", options=options):
                events.append(e)

            session_id = next((e.session_id for e in events if getattr(e, "type", "") == "system.init"), "")
            self.assertTrue(session_id)

            todo_file = store.session_dir(session_id) / "todos.json"
            self.assertTrue(todo_file.exists())
            data = json.loads(todo_file.read_text(encoding="utf-8"))
            self.assertEqual(len(data.get("todos") or []), 2)

    async def test_runtime_accepts_opencode_todo_shape(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgenticOptions(
                provider=OpenCodeTodoProvider(),
                model="fake",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                tools=default_tool_registry(),
                allowed_tools=["TodoWrite"],
            )
            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="todo", options=options):
                events.append(e)

            session_id = next((e.session_id for e in events if getattr(e, "type", "") == "system.init"), "")
            self.assertTrue(session_id)

            todo_file = store.session_dir(session_id) / "todos.json"
            data = json.loads(todo_file.read_text(encoding="utf-8"))
            todos = data.get("todos")
            self.assertIsInstance(todos, list)
            self.assertEqual({t.get("id") for t in todos if isinstance(t, dict)}, {"t1", "t2"})


if __name__ == "__main__":
    unittest.main()
