import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestCliProviderModelResolutionFromModelsDev(unittest.TestCase):
    def test_model_provider_model_uses_models_dev_provider_defaults(self) -> None:
        from openagentic_cli.config import build_options

        with TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OPENAGENTIC_SDK_HOME"] = str(root / "oa-home")
            os.environ["OPENCODE_TEST_HOME"] = str(root / "opencode-home")
            os.environ["XDG_CONFIG_HOME"] = str(root / "xdg")
            os.environ["OPENCODE_DISABLE_PROJECT_CONFIG"] = "1"
            os.environ["OPENCODE_DISABLE_MODELS_FETCH"] = "1"
            os.environ["OPENCODE_CONFIG_CONTENT"] = '{"model": "p1/m1"}'
            os.environ["P1_KEY"] = "k-from-env"
            os.environ.pop("RIGHTCODE_API_KEY", None)
            try:
                cache = Path(os.environ["OPENAGENTIC_SDK_HOME"]) / "cache"
                cache.mkdir(parents=True, exist_ok=True)
                (cache / "models.json").write_text(
                    json.dumps(
                        {
                            "p1": {
                                "id": "p1",
                                "name": "Provider 1",
                                "api": "https://example.invalid",
                                "env": ["P1_KEY"],
                                "models": {
                                    "m1": {
                                        "id": "m1",
                                        "name": "Model 1",
                                        "release_date": "2025-01-01",
                                        "attachment": False,
                                        "reasoning": True,
                                        "temperature": True,
                                        "tool_call": True,
                                        "limit": {"context": 10, "output": 10},
                                        "options": {},
                                        "headers": {},
                                    }
                                },
                            }
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

                opts = build_options(
                    cwd=str(root),
                    project_dir=str(root),
                    permission_mode="deny",
                    interactive=False,
                )

                self.assertEqual(getattr(opts.provider, "name", ""), "p1")
                self.assertEqual(opts.model, "m1")
                self.assertEqual(opts.api_key, "k-from-env")
            finally:
                os.environ.pop("OPENAGENTIC_SDK_HOME", None)
                os.environ.pop("OPENCODE_TEST_HOME", None)
                os.environ.pop("XDG_CONFIG_HOME", None)
                os.environ.pop("OPENCODE_DISABLE_PROJECT_CONFIG", None)
                os.environ.pop("OPENCODE_DISABLE_MODELS_FETCH", None)
                os.environ.pop("OPENCODE_CONFIG_CONTENT", None)
                os.environ.pop("P1_KEY", None)


if __name__ == "__main__":
    unittest.main()
