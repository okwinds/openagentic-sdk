import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestToolContextProjectDir(unittest.TestCase):
    def test_skill_defaults_to_ctx_project_dir(self) -> None:
        from openagentic_sdk.tools.base import ToolContext
        from openagentic_sdk.tools.defaults import default_tool_registry

        with TemporaryDirectory() as td:
            root = Path(td)
            skills_root = root / ".claude" / "skills" / "a"
            skills_root.mkdir(parents=True)
            (skills_root / "SKILL.md").write_text("# a\n\nsummary\n", encoding="utf-8")

            tools = default_tool_registry()
            out = tools.get("Skill").run_sync({"name": "a"}, ToolContext(cwd="/", project_dir=str(root)))
            self.assertEqual(out["name"], "a")

    def test_slash_command_defaults_to_ctx_project_dir(self) -> None:
        from openagentic_sdk.tools.base import ToolContext
        from openagentic_sdk.tools.defaults import default_tool_registry

        with TemporaryDirectory() as td:
            root = Path(td)
            cmd_root = root / ".claude" / "commands"
            cmd_root.mkdir(parents=True)
            (cmd_root / "hello.md").write_text("Hi", encoding="utf-8")

            tools = default_tool_registry()
            out = tools.get("SlashCommand").run_sync({"name": "hello"}, ToolContext(cwd="/", project_dir=str(root)))
            self.assertEqual(out["content"], "Hi")


if __name__ == "__main__":
    unittest.main()
