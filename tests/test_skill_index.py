import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.skills.index import index_skills


class TestSkillIndex(unittest.TestCase):
    def test_indexes_claude_skills(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".claude" / "skills" / "a"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text("# a\n\nsummary\n", encoding="utf-8")

            skills = index_skills(project_dir=str(root))
            self.assertEqual(len(skills), 1)
            self.assertEqual(skills[0].name, "a")
            self.assertTrue(skills[0].path.endswith("SKILL.md"))


if __name__ == "__main__":
    unittest.main()

