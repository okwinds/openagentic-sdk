from __future__ import annotations

import json
import threading
import time
import unittest
import urllib.error
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


def _http_any(url: str, method: str, payload: dict | None = None) -> tuple[int, dict[str, str], bytes]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            status = int(getattr(resp, "status", 200) or 200)
            raw = resp.read()
            hdrs = {k.lower(): v for k, v in dict(resp.headers).items()}
            return status, hdrs, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        hdrs = {k.lower(): v for k, v in dict(e.headers).items()}
        status = int(getattr(e, "code", 500) or 500)
        try:
            e.close()
        except Exception:
            pass
        return status, hdrs, raw


class TestVSCodeExtensionCompatEndpoints(unittest.TestCase):
    def test_app_and_tui_append_prompt_endpoints_exist(self) -> None:
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
            port = int(httpd.server_address[1])

            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{port}"

                status, hdrs, body = _http_any(base + "/app", "GET")
                self.assertEqual(status, 200)
                self.assertIn("content-type", hdrs)
                self.assertIn("text/html", hdrs["content-type"])
                self.assertIn(b"openagentic-sdk", body)

                status2, _hdrs2, body2 = _http_any(base + "/tui/append-prompt", "POST", {"text": "hi"})
                self.assertEqual(status2, 200)
                obj = json.loads(body2.decode("utf-8", errors="replace"))
                self.assertTrue(obj.get("ok"))
                sid = obj.get("session_id")
                self.assertIsInstance(sid, str)

                # Ensure the async prompt produces at least one assistant message.
                deadline = time.time() + 3.0
                saw = False
                while time.time() < deadline:
                    status3, _hdrs3, body3 = _http_any(base + f"/session/{sid}/events", "GET")
                    self.assertEqual(status3, 200)
                    evs = json.loads(body3.decode("utf-8", errors="replace")).get("events")
                    if isinstance(evs, list) and any(isinstance(e, dict) and e.get("type") == "assistant.message" for e in evs):
                        saw = True
                        break
                    time.sleep(0.05)
                self.assertTrue(saw)
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
