import unittest

from openagentic_sdk.skills.parse import parse_skill_markdown


SKILL_MD = """# skill-example

One line summary.

## Checklist
- Do A
- Do B

## Notes
Use the Read tool first.
"""


class TestSkillParser(unittest.TestCase):
    def test_parses_name_summary_checklist(self) -> None:
        s = parse_skill_markdown(SKILL_MD)
        self.assertEqual(s.name, "skill-example")
        self.assertEqual(s.summary, "One line summary.")
        self.assertEqual(s.checklist, ["Do A", "Do B"])

    def test_frontmatter_name_takes_precedence(self) -> None:
        md = "---\nname: main-process\ndescription: demo\n---\n\n# Main Process\n\nSummary.\n"
        s = parse_skill_markdown(md)
        self.assertEqual(s.name, "main-process")
        self.assertEqual(s.description, "demo")


if __name__ == "__main__":
    unittest.main()
