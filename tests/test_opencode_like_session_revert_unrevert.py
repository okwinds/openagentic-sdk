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


def _json_req(url: str, method: str, payload: dict | None = None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
        raw = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace")) if raw else None


class TestOpenCodeLikeSessionRevert(unittest.TestCase):
    def test_revert_and_unrevert_change_message_view(self) -> None:
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

                _ = _json_req(base + f"/session/{sid}/message", "POST", {"prompt": "one"})
                _ = _json_req(base + f"/session/{sid}/message", "POST", {"prompt": "two"})

                msgs = _json_req(base + f"/session/{sid}/message", "GET")
                user_msgs = [m for m in msgs if isinstance(m, dict) and m.get("info", {}).get("role") == "user"]
                self.assertGreaterEqual(len(user_msgs), 2)
                first_user_id = user_msgs[0].get("info", {}).get("id")
                self.assertIsInstance(first_user_id, str)

                _ = _json_req(base + f"/session/{sid}/revert", "POST", {"messageID": first_user_id})
                msgs2 = _json_req(base + f"/session/{sid}/message", "GET")
                texts2 = []
                for m in msgs2:
                    if not isinstance(m, dict):
                        continue
                    for p in m.get("parts") or []:
                        if isinstance(p, dict) and p.get("type") == "text":
                            texts2.append(p.get("text"))
                self.assertNotIn("two", texts2)

                _ = _json_req(base + f"/session/{sid}/unrevert", "POST", {})
                msgs3 = _json_req(base + f"/session/{sid}/message", "GET")
                texts3 = []
                for m in msgs3:
                    if not isinstance(m, dict):
                        continue
                    for p in m.get("parts") or []:
                        if isinstance(p, dict) and p.get("type") == "text":
                            texts3.append(p.get("text"))
                self.assertIn("two", texts3)
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
