import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.tools.base import ToolContext
from open_agent_sdk.tools.skill_load import SkillLoadTool


class TestSkillTools(unittest.TestCase):
    def test_skill_load(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".claude" / "skills" / "ex"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text("# ex\n\nsummary\n\n## Checklist\n- A\n", encoding="utf-8")
            tool = SkillLoadTool()
            out = tool.run_sync({"name": "ex", "project_dir": str(root)}, ToolContext(cwd=str(root)))
            self.assertEqual(out["name"], "ex")
            self.assertEqual(out["summary"], "summary")
            self.assertEqual(out["checklist"], ["A"])
            self.assertIn("content", out)


if __name__ == "__main__":
    unittest.main()

