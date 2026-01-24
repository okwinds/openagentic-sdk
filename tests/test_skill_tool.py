import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.skill import SkillTool


class TestSkillTool(unittest.TestCase):
    def test_load(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".claude" / "skills" / "main-process"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text(
                "---\nname: main-process\ndescription: desc\n---\n\n# Main Process\n\nSummary.\n",
                encoding="utf-8",
            )

            tool = SkillTool()
            loaded = tool.run_sync({"name": "main-process"}, ToolContext(cwd="/", project_dir=str(root)))
            self.assertEqual(loaded["name"], "main-process")
            self.assertEqual(loaded["description"], "desc")
            self.assertIn("SKILL.md", loaded["path"])
            self.assertIn("Base directory", loaded["output"])

    def test_missing_name_errors(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".claude" / "skills" / "a"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text("---\nname: a\ndescription: d\n---\n", encoding="utf-8")

            tool = SkillTool()
            with self.assertRaises(ValueError):
                tool.run_sync({}, ToolContext(cwd="/", project_dir=str(root)))


if __name__ == "__main__":
    unittest.main()
