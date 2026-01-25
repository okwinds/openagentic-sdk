import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestProviderListingConfigOverrides(unittest.TestCase):
    def test_whitelist_blacklist_and_variant_disable(self) -> None:
        from openagentic_sdk.providers.catalog import build_provider_listing

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
                                        "limit": {"context": 10, "output": 10},
                                        "options": {},
                                        "headers": {},
                                        "variants": {"fast": {}, "slow": {}},
                                    },
                                    "m2": {
                                        "id": "m2",
                                        "name": "Model 2",
                                        "release_date": "2025-01-01",
                                        "attachment": False,
                                        "reasoning": True,
                                        "temperature": True,
                                        "tool_call": True,
                                        "limit": {"context": 10, "output": 10},
                                        "options": {},
                                        "headers": {},
                                    },
                                },
                            }
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

                # Whitelist should keep only m2.
                listing = build_provider_listing(
                    {
                        "provider": {"p1": {"whitelist": ["m2"]}},
                    }
                )
                p1 = next(p for p in listing["all"] if p.get("id") == "p1")
                self.assertEqual(sorted((p1.get("models") or {}).keys()), ["m2"])

                # Blacklist should remove m1.
                listing2 = build_provider_listing(
                    {
                        "provider": {"p1": {"blacklist": ["m1"]}},
                    }
                )
                p1b = next(p for p in listing2["all"] if p.get("id") == "p1")
                self.assertEqual(sorted((p1b.get("models") or {}).keys()), ["m2"])

                # Variant disabling in config should drop that variant.
                listing3 = build_provider_listing(
                    {
                        "provider": {
                            "p1": {
                                "models": {
                                    "m1": {"variants": {"slow": {"disabled": True}}}
                                }
                            }
                        },
                    }
                )
                p1c = next(p for p in listing3["all"] if p.get("id") == "p1")
                m1 = (p1c.get("models") or {}).get("m1")
                self.assertIsInstance(m1, dict)
                assert isinstance(m1, dict)
                variants = m1.get("variants")
                self.assertIsInstance(variants, dict)
                assert isinstance(variants, dict)
                self.assertIn("fast", variants)
                self.assertNotIn("slow", variants)
            finally:
                os.environ.pop("OPENAGENTIC_SDK_HOME", None)
                os.environ.pop("OPENCODE_DISABLE_MODELS_FETCH", None)


if __name__ == "__main__":
    unittest.main()
