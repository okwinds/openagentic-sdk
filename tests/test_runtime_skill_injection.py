import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.sessions.store import FileSessionStore


class RecordingProvider:
    name = "recording"

    def __init__(self) -> None:
        self.seen = []

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self.seen.append(list(messages))
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestRuntimeSkillInjection(unittest.IsolatedAsyncioTestCase):
    async def test_injects_memory_and_skill_index(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "CLAUDE.md").write_text("project memory", encoding="utf-8")
            skill_dir = root / ".claude" / "skills" / "example"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# example\n\nSummary line.\n", encoding="utf-8")
            cmd_dir = root / ".claude" / "commands"
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "hello.md").write_text("hello", encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            provider = RecordingProvider()
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

            async for _ in openagentic_sdk.query(prompt="hi", options=options):
                pass

            first_call_msgs = provider.seen[0]
            self.assertEqual(first_call_msgs[0]["role"], "system")
            sys = first_call_msgs[0]["content"]
            self.assertIn("project memory", sys)
            self.assertIn("example", sys)
            self.assertIn("/hello", sys)


if __name__ == "__main__":
    unittest.main()

