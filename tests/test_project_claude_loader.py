import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.project.claude import load_claude_project_settings


class TestClaudeProjectLoader(unittest.TestCase):
    def test_loads_memory_skills_commands(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "CLAUDE.md").write_text("memory", encoding="utf-8")
            (root / ".claude" / "skills" / "example").mkdir(parents=True)
            (root / ".claude" / "skills" / "example" / "SKILL.md").write_text("# Example", encoding="utf-8")
            (root / ".claude" / "commands").mkdir(parents=True)
            (root / ".claude" / "commands" / "hello.md").write_text("hi", encoding="utf-8")

            s = load_claude_project_settings(str(root))
            self.assertEqual(s.memory, "memory")
            self.assertEqual([x.name for x in s.skills], ["example"])
            self.assertEqual([x.name for x in s.commands], ["hello"])


if __name__ == "__main__":
    unittest.main()

