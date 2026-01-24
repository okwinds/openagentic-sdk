from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from openagentic_sdk.providers.registry import list_configured_models, list_model_variants


class TestProviderRegistry(unittest.TestCase):
    def test_lists_models_and_variants_from_config(self) -> None:
        cfg = {
            "provider": {
                "p1": {
                    "options": {"baseURL": "http://example", "apiKey": "k"},
                    "models": {
                        "m1": {"variants": {"fast": {"disabled": False}, "slow": {"disabled": True}}},
                        "m2": {},
                    },
                }
            }
        }
        self.assertEqual(list_configured_models(cfg), ["m1", "m2"])
        self.assertEqual(list_model_variants(cfg, model="m1"), ["fast"])


class TestCliProviderSelection(unittest.TestCase):
    def test_build_options_can_use_provider_options_baseurl_apikey(self) -> None:
        from openagentic_cli.config import build_options

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OPENCODE_CONFIG_DIR"] = str(root / "global")
            os.environ["OA_PROVIDER"] = "p1"
            # Ensure we don't depend on RIGHTCODE_* env vars.
            os.environ.pop("RIGHTCODE_API_KEY", None)

            (root / "opencode.json").write_text(
                """
{
  "provider": {
    "p1": {
      "options": {
        "baseURL": "http://127.0.0.1:1234",
        "apiKey": "from-config",
        "timeout": 1000
      }
    }
  },
  "model": "m"
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            opts = build_options(cwd=str(root), project_dir=str(root), permission_mode="deny")
            self.assertEqual(opts.api_key, "from-config")
            self.assertEqual(getattr(opts.provider, "base_url", None), "http://127.0.0.1:1234")
        os.environ.pop("OPENCODE_CONFIG_DIR", None)
        os.environ.pop("OA_PROVIDER", None)


if __name__ == "__main__":
    unittest.main()
