from __future__ import annotations

import json
import os
import threading
import unittest
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.server.http_server import OpenAgenticHttpServer
from openagentic_sdk.sessions.store import FileSessionStore


class _Provider:
    name = "test-provider"

    async def complete(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 1}, raw=None)


def _http_json(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        raw = resp.read()
    obj = json.loads(raw.decode("utf-8", errors="replace"))
    assert isinstance(obj, dict)
    return obj


class TestHttpServerProviderModelsList(unittest.TestCase):
    def test_provider_list_includes_models_dev_models(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OPENAGENTIC_SDK_HOME"] = str(root / "oa-home")
            os.environ["OPENCODE_TEST_HOME"] = str(root / "opencode-home")
            os.environ["XDG_CONFIG_HOME"] = str(root / "xdg")
            os.environ["OPENCODE_DISABLE_PROJECT_CONFIG"] = "1"
            os.environ["OPENCODE_DISABLE_MODELS_FETCH"] = "1"
            os.environ["OPENCODE_CONFIG_CONTENT"] = (
                '{'
                '  "provider": {'
                '    "p1": {"options": {"baseURL": "https://example.invalid", "apiKey": "k1"}}'
                '  }'
                '}'
            )
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

                store = FileSessionStore(root_dir=root)
                opts = OpenAgenticOptions(
                    provider=_Provider(),
                    model="m",
                    api_key="x",
                    cwd=str(root),
                    project_dir=str(root),
                    session_store=store,
                    permission_gate=PermissionGate(permission_mode="bypass"),
                )
                server = OpenAgenticHttpServer(options=opts, host="127.0.0.1", port=0)
                httpd = server.serve_forever()
                port = httpd.server_address[1]

                t = threading.Thread(target=httpd.serve_forever, daemon=True)
                t.start()
                try:
                    base = f"http://127.0.0.1:{port}"
                    data = _http_json(base + "/provider")
                    self.assertIn("all", data)
                    self.assertIn("default", data)
                    self.assertIn("connected", data)

                    all_providers = data["all"]
                    self.assertIsInstance(all_providers, list)
                    p1 = None
                    for p in all_providers:
                        if isinstance(p, dict) and p.get("id") == "p1":
                            p1 = p
                    self.assertIsNotNone(p1)
                    assert isinstance(p1, dict)

                    # Must include models.dev-backed models.
                    models = p1.get("models")
                    self.assertIsInstance(models, dict)
                    self.assertIn("m1", models)

                    # Must not leak raw api keys.
                    self.assertNotIn("key", p1)
                    self.assertNotIn("apiKey", json.dumps(p1))
                finally:
                    httpd.shutdown()
                    httpd.server_close()
            finally:
                os.environ.pop("OPENAGENTIC_SDK_HOME", None)
                os.environ.pop("OPENCODE_TEST_HOME", None)
                os.environ.pop("XDG_CONFIG_HOME", None)
                os.environ.pop("OPENCODE_DISABLE_PROJECT_CONFIG", None)
                os.environ.pop("OPENCODE_DISABLE_MODELS_FETCH", None)
                os.environ.pop("OPENCODE_CONFIG_CONTENT", None)


if __name__ == "__main__":
    unittest.main()
