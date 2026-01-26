import tempfile
import unittest
from pathlib import Path


class TestProjectSystemPromptSkills(unittest.TestCase):
    def test_system_prompt_does_not_index_skills(self) -> None:
        from openagentic_sdk.options import OpenAgenticOptions
        from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider
        from openagentic_sdk.runtime import _build_project_system_prompt

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude" / "skills" / "demo").mkdir(parents=True)
            (root / ".claude" / "skills" / "demo" / "SKILL.md").write_text(
                "---\nname: demo\n---\n\n# Demo\n",
                encoding="utf-8",
            )
            opts = OpenAgenticOptions(
                provider=OpenAICompatibleProvider(),
                model="m",
                api_key="k",
                cwd=str(root),
                project_dir=str(root),
                setting_sources=["project"],
            )
            built = _build_project_system_prompt(opts)
            # The system prompt may exist (env block, config rules, etc), but it
            # should not enumerate skills.
            self.assertNotIn("demo", built.system_text or "")


if __name__ == "__main__":
    unittest.main()
