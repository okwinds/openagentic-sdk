import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestExecuteSkillPromptExpand(unittest.TestCase):
    def test_expands_execute_skill_prompt_when_skill_exists(self) -> None:
        from open_agent_sdk.options import OpenAgentOptions
        from open_agent_sdk.providers.openai_compatible import OpenAICompatibleProvider
        from open_agent_sdk.runtime import _maybe_expand_execute_skill_prompt

        with TemporaryDirectory() as td:
            root = Path(td)
            skill_dir = root / ".claude" / "skills" / "main-process"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: main-process\n---\n\n# Main Process\n\n## Workflow\n- x\n", encoding="utf-8")

            opts = OpenAgentOptions(
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
        from open_agent_sdk.options import OpenAgentOptions
        from open_agent_sdk.providers.openai_compatible import OpenAICompatibleProvider
        from open_agent_sdk.runtime import _maybe_expand_execute_skill_prompt

        opts = OpenAgentOptions(provider=OpenAICompatibleProvider(), model="m", api_key="k", cwd=".")
        self.assertEqual(_maybe_expand_execute_skill_prompt("hello", opts), "hello")


if __name__ == "__main__":
    unittest.main()

