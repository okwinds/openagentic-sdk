import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestCliCompactionLimitsFromModelsDev(unittest.TestCase):
    def test_build_options_derives_limits_from_models_dev(self) -> None:
        from openagentic_cli.config import build_options

        with TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OPENAGENTIC_SDK_HOME"] = str(root / "oa-home")
            os.environ["OPENCODE_TEST_HOME"] = str(root / "opencode-home")
            os.environ["XDG_CONFIG_HOME"] = str(root / "xdg")
            os.environ["OPENCODE_DISABLE_PROJECT_CONFIG"] = "1"
            os.environ["OPENCODE_DISABLE_MODELS_FETCH"] = "1"
            os.environ["OPENCODE_CONFIG_CONTENT"] = (
                '{'
                '  "model": "p1/m1",'
                '  "provider": {'
                '    "p1": {"options": {"baseURL": "https://example.invalid", "apiKey": "k1"}}'
                '  }'
                '}'
            )
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
                                "env": [],
                                "models": {
                                    "m1": {
                                        "id": "m1",
                                        "name": "Model 1",
                                        "release_date": "2025-01-01",
                                        "attachment": False,
                                        "reasoning": True,
                                        "temperature": True,
                                        "tool_call": True,
                                        "limit": {"context": 999, "output": 111},
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

                # Post-v2-08 behavior: if compaction.context_limit/output_limit are unset,
                # derive them from model metadata.
                self.assertEqual(opts.compaction.context_limit, 999)
                self.assertEqual(opts.compaction.output_limit, 111)
            finally:
                os.environ.pop("OPENAGENTIC_SDK_HOME", None)
                os.environ.pop("OPENCODE_TEST_HOME", None)
                os.environ.pop("XDG_CONFIG_HOME", None)
                os.environ.pop("OPENCODE_DISABLE_PROJECT_CONFIG", None)
                os.environ.pop("OPENCODE_DISABLE_MODELS_FETCH", None)
                os.environ.pop("OPENCODE_CONFIG_CONTENT", None)


if __name__ == "__main__":
    unittest.main()
