from __future__ import annotations

import json
import threading
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


def _json_req(url: str, method: str, payload: dict | None = None):
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
    return json.loads(raw.decode("utf-8", errors="replace")) if raw else None


class TestOpenCodeLikeSessionShare(unittest.TestCase):
    def test_share_and_unshare(self) -> None:
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
            httpd = OpenAgenticHttpServer(options=opts, host="127.0.0.1", port=0).serve_forever()
            port = int(httpd.server_address[1])
            th = threading.Thread(target=httpd.serve_forever, daemon=True)
            th.start()
            try:
                base = f"http://127.0.0.1:{port}"
                sid = _json_req(base + "/session", "POST", {}).get("id")
                info = _json_req(base + f"/session/{sid}/share", "POST", {})
                self.assertIsInstance(info, dict)
                share_id = info.get("metadata", {}).get("share_id")
                self.assertIsInstance(share_id, str)

                payload = _json_req(base + f"/share/{share_id}", "GET")
                self.assertIsInstance(payload, dict)
                self.assertEqual(payload.get("session_id"), sid)

                _ = _json_req(base + f"/session/{sid}/share", "DELETE")
                payload2 = _json_req(base + f"/share/{share_id}", "GET")
                # Should fail after unshare.
                self.assertIsInstance(payload2, dict)
                self.assertEqual(payload2.get("error"), "not_found")
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
