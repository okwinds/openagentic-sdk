from __future__ import annotations

import asyncio
import json
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.server.http_server import OpenAgenticHttpServer
from openagentic_sdk.sessions.store import FileSessionStore


class _SlowProvider:
    name = "slow"

    async def complete(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        await asyncio.sleep(0.2)
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
    return json.loads(raw.decode("utf-8", errors="replace"))


class TestOpenCodeLikeSessionMessageView(unittest.TestCase):
    def test_prompt_async_populates_message_view(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)

            opts = OpenAgenticOptions(
                provider=_SlowProvider(),
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
            th = threading.Thread(target=httpd.serve_forever, daemon=True)
            th.start()
            try:
                base = f"http://127.0.0.1:{port}"
                created = _json_req(base + "/session", "POST", {})
                sid = created.get("id")
                self.assertIsInstance(sid, str)

                # prompt_async should return 204.
                data = json.dumps({"prompt": "hi"}).encode("utf-8")
                req = urllib.request.Request(
                    base + f"/session/{sid}/prompt_async",
                    method="POST",
                    data=data,
                    headers={"content-type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                    self.assertEqual(getattr(resp, "status", None), 204)

                # Poll until the assistant message appears in the OpenCode-like view.
                deadline = time.time() + 3.0
                while time.time() < deadline:
                    msgs = _json_req(base + f"/session/{sid}/message", "GET")
                    if isinstance(msgs, list) and any(
                        isinstance(m, dict)
                        and isinstance(m.get("info"), dict)
                        and m.get("info", {}).get("role") == "assistant"
                        for m in msgs
                    ):
                        break
                    time.sleep(0.05)
                else:
                    raise AssertionError("assistant message did not appear")
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
