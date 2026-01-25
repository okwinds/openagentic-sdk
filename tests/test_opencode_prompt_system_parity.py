import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider


class _NameOnlyProvider:
    # Minimal provider stub for prompt system tests.
    def __init__(self, name: str) -> None:
        self.name = name


class TestOpenCodePromptSystemParity(unittest.TestCase):
    def test_environment_block_contains_expected_fields(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()

            options = OpenAgenticOptions(
                provider=OpenAICompatibleProvider(),
                model="gpt-test",
                api_key="k",
                cwd=str(root),
                project_dir=str(root),
                setting_sources=["project"],
            )

            from openagentic_sdk.prompt_system import build_system_prompt_text

            text = build_system_prompt_text(options) or ""
            self.assertIn("<env>", text)
            self.assertIn(f"Working directory: {root.resolve()}", text)
            self.assertIn("Is directory a git repo: yes", text)
            # Match OpenCode's Node `process.platform` values.
            self.assertIn(f"Platform: {sys.platform}", text)
            self.assertIn("Today's date:", text)

    def test_local_rules_stop_at_first_kind(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            leaf = root / "a" / "b"
            leaf.mkdir(parents=True)

            # Multiple matches for the chosen rule-file kind.
            (root / "AGENTS.md").write_text("agents-top", encoding="utf-8")
            (root / "a" / "AGENTS.md").write_text("agents-mid", encoding="utf-8")

            # These exist, but should be ignored because AGENTS.md is present.
            (root / "CLAUDE.md").write_text("claude-top", encoding="utf-8")
            (root / "CONTEXT.md").write_text("context-top", encoding="utf-8")

            env = {
                # Keep global rules/config hermetic.
                "XDG_CONFIG_HOME": str(root / "xdg"),
                "OPENCODE_TEST_HOME": str(root / "home"),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                options = OpenAgenticOptions(
                    provider=OpenAICompatibleProvider(),
                    model="gpt-test",
                    api_key="k",
                    cwd=str(leaf),
                    project_dir=str(root),
                    setting_sources=["project"],
                )

                from openagentic_sdk.prompt_system import build_system_prompt_text

                text = build_system_prompt_text(options) or ""
                self.assertIn("Instructions from:", text)
                self.assertIn("agents-top", text)
                self.assertIn("agents-mid", text)
                self.assertNotIn("claude-top", text)
                self.assertNotIn("context-top", text)

    def test_global_rules_first_existing_only(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            xdg = root / "xdg"
            home = root / "home"
            cfg_dir = root / "cfg"

            (xdg / "opencode").mkdir(parents=True)
            (xdg / "opencode" / "AGENTS.md").write_text("xdg-agents", encoding="utf-8")

            (home / ".claude").mkdir(parents=True)
            (home / ".claude" / "CLAUDE.md").write_text("home-claude", encoding="utf-8")

            cfg_dir.mkdir(parents=True)
            (cfg_dir / "AGENTS.md").write_text("cfg-agents", encoding="utf-8")

            env = {
                "XDG_CONFIG_HOME": str(xdg),
                "OPENCODE_TEST_HOME": str(home),
                "OPENCODE_CONFIG_DIR": str(cfg_dir),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                options = OpenAgenticOptions(
                    provider=OpenAICompatibleProvider(),
                    model="gpt-test",
                    api_key="k",
                    cwd=str(root),
                    project_dir=str(root),
                    setting_sources=["project"],
                )

                from openagentic_sdk.prompt_system import build_system_prompt_text

                text = build_system_prompt_text(options) or ""
                self.assertIn("xdg-agents", text)
                self.assertNotIn("home-claude", text)
                self.assertNotIn("cfg-agents", text)

    def test_url_instructions_included_only_when_fetch_nonempty(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            url = "https://example.com/instructions"

            env = {
                "OPENCODE_CONFIG_CONTENT": '{"instructions": ["' + url + '"]}',
                "XDG_CONFIG_HOME": str(root / "xdg"),
                "OPENCODE_TEST_HOME": str(root / "home"),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                options = OpenAgenticOptions(
                    provider=OpenAICompatibleProvider(),
                    model="gpt-test",
                    api_key="k",
                    cwd=str(root),
                    project_dir=str(root),
                    setting_sources=["project"],
                )

                from openagentic_sdk import prompt_system

                seen = []

                def fake_fetch(u: str, *, timeout_s: float) -> str:
                    seen.append({"u": u, "timeout_s": timeout_s})
                    return "URL-TEXT" if u == url else ""

                with mock.patch.object(prompt_system, "_fetch_text", side_effect=fake_fetch):
                    text = prompt_system.build_system_prompt_text(options) or ""
                self.assertIn("Instructions from: " + url, text)
                self.assertIn("URL-TEXT", text)
                self.assertTrue(seen)
                self.assertEqual(seen[0]["u"], url)
                self.assertEqual(seen[0]["timeout_s"], 5.0)

                # Empty fetch should not emit an instruction block.
                seen.clear()
                with mock.patch.object(prompt_system, "_fetch_text", return_value=""):
                    text2 = prompt_system.build_system_prompt_text(options) or ""
                self.assertNotIn("Instructions from: " + url, text2)
                self.assertNotIn("URL-TEXT", text2)

    def test_provider_prompt_selection_and_header(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            options = OpenAgenticOptions(
                provider=_NameOnlyProvider("anthropic"),
                model="claude-3-5-sonnet",
                api_key="k",
                cwd=str(root),
                project_dir=str(root),
                setting_sources=["project"],
            )

            from openagentic_sdk.prompt_system import build_system_prompt_text

            text = build_system_prompt_text(options) or ""
            # Header spoof for anthropic.
            self.assertIn("You are Claude Code", text)
            # Provider prompt selection for claude models.
            self.assertIn("You are opencode", text)


if __name__ == "__main__":
    unittest.main()
