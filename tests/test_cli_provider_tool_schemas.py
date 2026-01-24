import os
import unittest


class TestCliProviderToolSchemas(unittest.TestCase):
    def test_rightcode_provider_is_openai_compatible(self) -> None:
        from openagentic_cli.config import build_options

        os.environ["RIGHTCODE_API_KEY"] = "x"
        os.environ["OPENCODE_CONFIG_DIR"] = os.getcwd()  # isolate from user home config
        try:
            opts = build_options(cwd=".", project_dir=".", permission_mode="deny")
            self.assertEqual(getattr(opts.provider, "name", None), "openai-compatible")
            self.assertEqual(type(opts.provider).__name__, "OpenAIResponsesProvider")
        finally:
            os.environ.pop("RIGHTCODE_API_KEY", None)
            os.environ.pop("OPENCODE_CONFIG_DIR", None)


if __name__ == "__main__":
    unittest.main()
