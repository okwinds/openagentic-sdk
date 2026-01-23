import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgentOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class FakeProvider:
    name = "fake"

    def __init__(self) -> None:
        self.seen_messages = []
        self.calls = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self.seen_messages.append(list(messages))
        self.calls += 1
        if self.calls == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall("tc1", "Read", {"file_path": "a.txt"})],
            )
        return ModelOutput(assistant_text="done", tool_calls=[])


class TestResumeRebuild(unittest.IsolatedAsyncioTestCase):
    async def test_resume_rebuilds_messages(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            store = FileSessionStore(root_dir=root)

            provider1 = FakeProvider()
            options1 = OpenAgentOptions(
                provider=provider1,
                model="fake",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
            )

            import openagentic_sdk

            events1 = []
            async for e in openagentic_sdk.query(prompt="read it", options=options1):
                events1.append(e)
            sid = next(e.session_id for e in events1 if getattr(e, "type", None) == "system.init")

            provider2 = FakeProvider()
            options2 = OpenAgentOptions(
                provider=provider2,
                model="fake",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
                resume=sid,
            )

            async for _ in openagentic_sdk.query(prompt="continue", options=options2):
                pass

            first = provider2.seen_messages[0]
            roles = [m.get("role") for m in first]
            self.assertIn("tool", roles)
            # Ensure tool results have a preceding assistant tool_calls message (OpenAI-compatible requirement).
            tool_idx = next(i for i, m in enumerate(first) if m.get("role") == "tool")
            self.assertGreater(tool_idx, 0)
            prev = first[tool_idx - 1]
            self.assertEqual(prev.get("role"), "assistant")
            tool_calls = prev.get("tool_calls")
            self.assertIsInstance(tool_calls, list)
            self.assertTrue(any(isinstance(tc, dict) and tc.get("id") == "tc1" for tc in tool_calls))


if __name__ == "__main__":
    unittest.main()
