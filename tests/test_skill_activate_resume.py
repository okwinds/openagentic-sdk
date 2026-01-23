import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.options import OpenAgentOptions
from open_agent_sdk.permissions.gate import PermissionGate
from open_agent_sdk.providers.base import ModelOutput, ToolCall
from open_agent_sdk.sessions.store import FileSessionStore


class ActivateProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self.calls += 1
        if self.calls == 1:
            return ModelOutput(assistant_text=None, tool_calls=[ToolCall("t1", "SkillActivate", {"name": "ex"})])
        return ModelOutput(assistant_text="done", tool_calls=[])


class RecordingProvider:
    name = "recording"

    def __init__(self) -> None:
        self.seen = []

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self.seen.append(list(messages))
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestSkillActivateResume(unittest.IsolatedAsyncioTestCase):
    async def test_resume_keeps_active_skills(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            skill_dir = root / ".claude" / "skills" / "ex"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# ex\n\nsummary\n", encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            options1 = OpenAgentOptions(
                provider=ActivateProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                setting_sources=["project"],
                project_dir=str(root),
            )
            import open_agent_sdk

            events = []
            async for e in open_agent_sdk.query(prompt="hi", options=options1):
                events.append(e)
            sid = next(e.session_id for e in events if getattr(e, "type", None) == "system.init")

            rp = RecordingProvider()
            options2 = OpenAgentOptions(
                provider=rp,
                model="m",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                setting_sources=["project"],
                project_dir=str(root),
                resume=sid,
            )

            async for _ in open_agent_sdk.query(prompt="next", options=options2):
                pass

            sys = rp.seen[0][0]["content"]
            self.assertIn("Active Skills", sys)
            self.assertIn("ex", sys)


if __name__ == "__main__":
    unittest.main()

