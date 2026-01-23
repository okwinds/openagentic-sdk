import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestExecuteSkillPromptExpand(unittest.TestCase):
    def test_expands_execute_skill_prompt_when_skill_exists(self) -> None:
        from openagentic_sdk.options import OpenAgenticOptions
        from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider
        from openagentic_sdk.runtime import _maybe_expand_execute_skill_prompt

        with TemporaryDirectory() as td:
            root = Path(td)
            skill_dir = root / ".claude" / "skills" / "main-process"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: main-process\n---\n\n# Main Process\n\n## Workflow\n- x\n", encoding="utf-8")

            opts = OpenAgenticOptions(
                provider=OpenAICompatibleProvider(),
                model="m",
                api_key="k",
                cwd=str(root),
                project_dir=str(root),
                setting_sources=["project"],
            )
            out = _maybe_expand_execute_skill_prompt("执行技能main-process", opts)
            self.assertIn("SKILL.md:", out)
            self.assertIn("name: main-process", out)

    def test_does_not_expand_other_prompts(self) -> None:
        from openagentic_sdk.options import OpenAgenticOptions
        from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider
        from openagentic_sdk.runtime import _maybe_expand_execute_skill_prompt

        opts = OpenAgenticOptions(provider=OpenAICompatibleProvider(), model="m", api_key="k", cwd=".")
        self.assertEqual(_maybe_expand_execute_skill_prompt("hello", opts), "hello")

    def test_expands_list_skills_prompt_when_skills_exist(self) -> None:
        from openagentic_sdk.options import OpenAgenticOptions
        from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider
        from openagentic_sdk.runtime import _maybe_expand_list_skills_prompt

        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".claude" / "skills" / "a"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text("---\nname: a\ndescription: desc\n---\n\n# A\n", encoding="utf-8")
            opts = OpenAgenticOptions(
                provider=OpenAICompatibleProvider(),
                model="m",
                api_key="k",
                cwd=str(root),
                project_dir=str(root),
                setting_sources=["project"],
            )
            out = _maybe_expand_list_skills_prompt("What Skills are available?", opts)
            self.assertIn("Skill", out)
            self.assertIn("action='list'", out)


if __name__ == "__main__":
    unittest.main()
