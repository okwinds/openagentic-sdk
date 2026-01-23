import os
import unittest


class TestCliConfig(unittest.TestCase):
    def test_rightcode_defaults(self) -> None:
        from openagentic_cli.config import build_options

        os.environ["RIGHTCODE_API_KEY"] = "x"
        try:
            opts = build_options(
                cwd=".",
                project_dir=".",
                permission_mode="prompt",
            )
            self.assertIsNotNone(opts.provider)
            self.assertEqual(opts.model, os.environ.get("RIGHTCODE_MODEL", "gpt-5.2"))
        finally:
            os.environ.pop("RIGHTCODE_API_KEY", None)

    def test_interactive_prompt_has_approver(self) -> None:
        from openagentic_cli.config import build_options

        os.environ["RIGHTCODE_API_KEY"] = "x"
        try:
            opts = build_options(
                cwd=".",
                project_dir=".",
                permission_mode="prompt",
                interactive=True,
            )
            self.assertTrue(opts.permission_gate.interactive)
            self.assertIsNotNone(opts.permission_gate.interactive_approver)
            self.assertTrue(opts.include_partial_messages)
        finally:
            os.environ.pop("RIGHTCODE_API_KEY", None)


if __name__ == "__main__":
    unittest.main()
