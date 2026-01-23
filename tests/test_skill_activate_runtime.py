import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class ActivateProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls = 0
        self.seen_messages = []

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self.seen_messages.append(list(messages))
        self.calls += 1
        if self.calls == 1:
            return ModelOutput(assistant_text=None, tool_calls=[ToolCall("t1", "SkillActivate", {"name": "ex"})])
        return ModelOutput(assistant_text="done", tool_calls=[])


class TestSkillActivateRuntime(unittest.IsolatedAsyncioTestCase):
    async def test_emits_skill_activated_and_updates_system_prompt(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            skill_dir = root / ".claude" / "skills" / "ex"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# ex\n\nsummary\n", encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            provider = ActivateProvider()
            options = OpenAgenticOptions(
                provider=provider,
                model="m",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                setting_sources=["project"],
                project_dir=str(root),
            )

            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="hi", options=options):
                events.append(e)

            types = [getattr(e, "type", None) for e in events]
            self.assertIn("skill.activated", types)
            self.assertGreaterEqual(len(provider.seen_messages), 2)
            sys2 = provider.seen_messages[1][0]["content"]
            self.assertIn("Active Skills", sys2)
            self.assertIn("ex", sys2)


if __name__ == "__main__":
    unittest.main()

