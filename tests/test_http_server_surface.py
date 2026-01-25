from __future__ import annotations

import json
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


def _http_json(url: str, method: str, payload: dict | None = None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace"))


class TestHttpServerSurface(unittest.TestCase):
    def test_session_routes(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
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
                health = _http_json(base + "/health", "GET")
                self.assertTrue(health.get("ok"))

                created = _http_json(base + "/session", "POST", {})
                sid = created.get("id")
                self.assertIsInstance(sid, str)

                resp = _http_json(base + f"/session/{sid}/message", "POST", {"prompt": "hi"})
                parts = resp.get("parts")
                self.assertIsInstance(parts, list)
                text = None
                for p in parts:
                    if isinstance(p, dict) and p.get("type") == "text":
                        text = p.get("text")
                self.assertEqual(text, "ok")

                sessions = _http_json(base + "/session", "GET")
                self.assertIsInstance(sessions, list)
                ids = [s.get("id") for s in sessions if isinstance(s, dict)]
                self.assertIn(sid, ids)

                evs = _http_json(base + f"/session/{sid}/events", "GET")
                self.assertIsInstance(evs.get("events"), list)
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
