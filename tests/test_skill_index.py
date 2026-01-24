import unittest
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.skills.index import index_skills


class TestSkillIndex(unittest.TestCase):
    def test_indexes_claude_skills(self) -> None:
        old_home = os.environ.pop("OPENAGENTIC_SDK_HOME", None)
        with TemporaryDirectory() as td:
            try:
                root = Path(td)
                p = root / ".claude" / "skills" / "a"
                p.mkdir(parents=True)
                (p / "SKILL.md").write_text("# a\n\nsummary\n", encoding="utf-8")

                skills = index_skills(project_dir=str(root))
                self.assertEqual(len(skills), 1)
                self.assertEqual(skills[0].name, "a")
                self.assertTrue(skills[0].path.endswith("SKILL.md"))
            finally:
                if old_home is not None:
                    os.environ["OPENAGENTIC_SDK_HOME"] = old_home

    def test_includes_global_skills(self) -> None:
        old_home = os.environ.pop("OPENAGENTIC_SDK_HOME", None)
        with TemporaryDirectory() as td:
            try:
                root = Path(td)
                home = root / ".home"
                os.environ["OPENAGENTIC_SDK_HOME"] = str(home)

                g = home / "skills" / "g"
                g.mkdir(parents=True)
                (g / "SKILL.md").write_text("---\nname: global-one\ndescription: gd\n---\n\n# global-one\n", encoding="utf-8")

                skills = index_skills(project_dir=str(root))
                names = [s.name for s in skills]
                self.assertIn("global-one", names)
            finally:
                if old_home is not None:
                    os.environ["OPENAGENTIC_SDK_HOME"] = old_home
                else:
                    os.environ.pop("OPENAGENTIC_SDK_HOME", None)

    def test_project_overrides_global_on_name_collision(self) -> None:
        old_home = os.environ.pop("OPENAGENTIC_SDK_HOME", None)
        with TemporaryDirectory() as td:
            try:
                root = Path(td)
                home = root / ".home"
                os.environ["OPENAGENTIC_SDK_HOME"] = str(home)

                g = home / "skills" / "a"
                g.mkdir(parents=True)
                (g / "SKILL.md").write_text("---\nname: a\ndescription: global\n---\n\n# A\n", encoding="utf-8")

                p = root / ".claude" / "skills" / "a"
                p.mkdir(parents=True)
                (p / "SKILL.md").write_text("---\nname: a\ndescription: project\n---\n\n# A\n", encoding="utf-8")

                skills = index_skills(project_dir=str(root))
                a = next(s for s in skills if s.name == "a")
                self.assertEqual(a.description, "project")
                self.assertIn(".claude", a.path)
            finally:
                if old_home is not None:
                    os.environ["OPENAGENTIC_SDK_HOME"] = old_home
                else:
                    os.environ.pop("OPENAGENTIC_SDK_HOME", None)


if __name__ == "__main__":
    unittest.main()
