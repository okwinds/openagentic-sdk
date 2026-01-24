import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.providers.openai_responses import OpenAIResponsesProvider


class TestSystemPromptLayering(unittest.TestCase):
    def test_builds_system_prompt_from_base_and_project_rules(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            # Project-scoped rules/memory.
            (root / "AGENTS.md").write_text("agents rules", encoding="utf-8")
            (root / "CLAUDE.md").write_text("claude memory", encoding="utf-8")
            (root / ".claude" / "commands").mkdir(parents=True)
            (root / ".claude" / "commands" / "hello.md").write_text("hi", encoding="utf-8")

            # Additional instruction files (resolved relative to project_dir).
            (root / "rules-extra.md").write_text("extra rules", encoding="utf-8")

            options = OpenAgenticOptions(
                provider=OpenAIResponsesProvider(),
                model="gpt-test",
                cwd=str(root),
                project_dir=str(root),
                setting_sources=["project"],
                system_prompt="BASE SYSTEM",
                instruction_files=["rules-extra.md"],
            )

            from openagentic_sdk.prompt_system import build_system_prompt_text

            text = build_system_prompt_text(options)
            self.assertIsInstance(text, str)
            self.assertIn("BASE SYSTEM", text)
            self.assertIn("agents rules", text)
            self.assertIn("claude memory", text)
            self.assertIn("/hello", text)
            self.assertIn("rules-extra.md", text)
            self.assertIn("extra rules", text)

    def test_omits_system_prompt_when_empty(self) -> None:
        options = OpenAgenticOptions(provider=OpenAIResponsesProvider(), model="gpt-test")

        from openagentic_sdk.prompt_system import build_system_prompt_text

        self.assertIsNone(build_system_prompt_text(options))


if __name__ == "__main__":
    unittest.main()
