import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestModelsDevCacheLoading(unittest.TestCase):
    def test_loads_from_cache_file(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OPENAGENTIC_SDK_HOME"] = str(root / "oa-home")
            os.environ["OPENCODE_DISABLE_MODELS_FETCH"] = "1"
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
                                        "limit": {"context": 123, "output": 456},
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

                from openagentic_sdk.providers.models_dev import get_models_dev

                providers = get_models_dev()
                self.assertIn("p1", providers)
                p = providers["p1"]
                self.assertEqual(p.get("id"), "p1")
                models = p.get("models")
                self.assertIsInstance(models, dict)
                m = models.get("m1")
                self.assertIsInstance(m, dict)
                assert isinstance(m, dict)
                lim = m.get("limit")
                self.assertIsInstance(lim, dict)
                assert isinstance(lim, dict)
                self.assertEqual(lim.get("context"), 123)
                self.assertEqual(lim.get("output"), 456)
            finally:
                os.environ.pop("OPENAGENTIC_SDK_HOME", None)
                os.environ.pop("OPENCODE_DISABLE_MODELS_FETCH", None)


if __name__ == "__main__":
    unittest.main()
