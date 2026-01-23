import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.skills.index import index_skills
from openagentic_sdk.skills.parse import parse_skill_markdown


class TestSkillMatrix(unittest.TestCase):
    def test_no_skills_dir_returns_empty(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            skills = index_skills(project_dir=str(root))
            self.assertEqual(skills, [])

    def test_missing_title_falls_back_to_dir_name(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".claude" / "skills" / "x"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text("no title here\n\nsummary\n", encoding="utf-8")
            skills = index_skills(project_dir=str(root))
            self.assertEqual(skills[0].name, "x")

    def test_checklist_missing_is_empty(self) -> None:
        s = parse_skill_markdown("# a\n\nsummary\n\n## Notes\nx\n")
        self.assertEqual(s.checklist, [])

    def test_checklist_ignores_blank_items(self) -> None:
        s = parse_skill_markdown("# a\n\nsummary\n\n## Checklist\n- A\n-\n-  \n- B\n")
        self.assertEqual(s.checklist, ["A", "B"])

    def test_summary_first_paragraph_only(self) -> None:
        s = parse_skill_markdown("# a\n\nfirst.\n\nsecond.\n")
        self.assertEqual(s.summary, "first.")

    def test_index_sorted_by_name(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            for name in ["b", "a"]:
                p = root / ".claude" / "skills" / name
                p.mkdir(parents=True)
                (p / "SKILL.md").write_text(f"# {name}\n\nsummary\n", encoding="utf-8")
            skills = index_skills(project_dir=str(root))
            self.assertEqual([s.name for s in skills], ["a", "b"])


if __name__ == "__main__":
    unittest.main()

