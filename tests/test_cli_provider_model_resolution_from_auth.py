import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestCliProviderModelResolutionFromAuth(unittest.TestCase):
    def test_model_provider_model_uses_auth_store(self) -> None:
        # This is OpenCode parity behavior:
        # - config.model can be "provider/model"
        # - if config provider options omit apiKey, auth.json can supply it
        from openagentic_cli.config import build_options
        from openagentic_sdk.auth import ApiAuth, set_auth

        with TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OPENAGENTIC_SDK_HOME"] = str(root / "home")
            # Make config loading hermetic (avoid reading real user configs/plugins).
            os.environ["OPENCODE_TEST_HOME"] = str(root / "opencode-home")
            os.environ["XDG_CONFIG_HOME"] = str(root / "xdg")
            os.environ["OPENCODE_DISABLE_PROJECT_CONFIG"] = "1"
            os.environ["OPENCODE_CONFIG_CONTENT"] = (
                '{'
                '  "model": "p1/m1",'
                '  "provider": {'
                '    "p1": {"options": {"baseURL": "https://example.invalid"}}'
                '  }'
                '}'
            )

            os.environ.pop("OPENCODE_CONFIG", None)
            os.environ.pop("OPENCODE_CONFIG_DIR", None)

            # Ensure legacy RIGHTCODE env is not required for this config path.
            os.environ.pop("RIGHTCODE_API_KEY", None)
            os.environ.pop("RIGHTCODE_MODEL", None)
            os.environ.pop("OA_PROVIDER", None)

            try:
                set_auth("p1", ApiAuth(key="api-from-auth"))
                opts = build_options(
                    cwd=str(root),
                    project_dir=str(root),
                    permission_mode="deny",
                    interactive=False,
                )

                # Expected post-v2-08 behavior: model ref selects provider and strips provider prefix.
                self.assertEqual(getattr(opts.provider, "name", ""), "p1")
                self.assertEqual(opts.model, "m1")
                self.assertEqual(opts.api_key, "api-from-auth")
            finally:
                os.environ.pop("OPENAGENTIC_SDK_HOME", None)
                os.environ.pop("OPENCODE_TEST_HOME", None)
                os.environ.pop("XDG_CONFIG_HOME", None)
                os.environ.pop("OPENCODE_DISABLE_PROJECT_CONFIG", None)
                os.environ.pop("OPENCODE_CONFIG_CONTENT", None)


if __name__ == "__main__":
    unittest.main()
