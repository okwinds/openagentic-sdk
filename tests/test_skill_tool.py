import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.skill import SkillTool


class TestSkillTool(unittest.TestCase):
    def test_list_and_load(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".claude" / "skills" / "main-process"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text(
                "---\nname: main-process\ndescription: desc\n---\n\n# Main Process\n\nSummary.\n",
                encoding="utf-8",
            )

            tool = SkillTool()
            listed = tool.run_sync({"action": "list"}, ToolContext(cwd="/", project_dir=str(root)))
            names = [s.get("name") for s in listed.get("skills") or []]
            self.assertIn("main-process", names)

            loaded = tool.run_sync({"action": "load", "name": "main-process"}, ToolContext(cwd="/", project_dir=str(root)))
            self.assertEqual(loaded["name"], "main-process")
            self.assertEqual(loaded["description"], "desc")
            self.assertIn("SKILL.md", loaded["path"])

    def test_list_with_empty_name_does_not_error(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".claude" / "skills" / "a"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text("---\nname: a\ndescription: d\n---\n", encoding="utf-8")

            tool = SkillTool()
            listed = tool.run_sync({"action": "list", "name": ""}, ToolContext(cwd="/", project_dir=str(root)))
            names = [s.get("name") for s in listed.get("skills") or []]
            self.assertEqual(names, ["a"])


if __name__ == "__main__":
    unittest.main()
