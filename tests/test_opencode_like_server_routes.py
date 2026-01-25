from __future__ import annotations

import json
import threading
import time
import unittest
import urllib.request
import urllib.error
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


def _http(url: str, method: str, payload: dict | None = None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            e.close()
        except Exception:
            pass
    return json.loads(raw.decode("utf-8", errors="replace"))


class TestOpenCodeLikeServerRoutes(unittest.TestCase):
    def test_global_health_session_status_patch_delete_and_event_sse(self) -> None:
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

                gh = _http(base + "/global/health", "GET")
                self.assertTrue(gh.get("healthy"))

                created = _http(base + "/session", "POST", {})
                sid = created.get("id")
                self.assertIsInstance(sid, str)

                status = _http(base + "/session/status", "GET")
                self.assertIsInstance(status, dict)
                self.assertEqual(status.get(sid, {}).get("type"), "idle")

                now = time.time()
                patched = _http(base + f"/session/{sid}", "PATCH", {"title": "t", "time": {"archived": now}})
                self.assertEqual(patched.get("title"), "t")
                self.assertEqual(patched.get("time", {}).get("archived"), now)

                # SSE: read the first event line.
                with urllib.request.urlopen(base + "/event", timeout=5) as resp:  # noqa: S310
                    line = resp.readline()
                self.assertIn(b"server.connected", line)

                _ = _http(base + f"/session/{sid}", "DELETE")
                sessions = _http(base + "/session", "GET")
                self.assertIsInstance(sessions, list)
                ids = [s.get("id") for s in sessions if isinstance(s, dict)]
                self.assertNotIn(sid, ids)

                # Path traversal / invalid session id is rejected.
                bad = _http(base + "/session/..", "GET")
                self.assertEqual(bad.get("error"), "invalid_session_id")
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
