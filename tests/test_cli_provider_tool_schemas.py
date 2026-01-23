import os
import unittest


class TestCliProviderToolSchemas(unittest.TestCase):
    def test_rightcode_provider_is_openai_compatible(self) -> None:
        from open_agent_cli.config import build_options

        os.environ["RIGHTCODE_API_KEY"] = "x"
        try:
            opts = build_options(cwd=".", project_dir=".", permission_mode="deny")
            self.assertEqual(getattr(opts.provider, "name", None), "openai-compatible")
        finally:
            os.environ.pop("RIGHTCODE_API_KEY", None)


if __name__ == "__main__":
    unittest.main()

