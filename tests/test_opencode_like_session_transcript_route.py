from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.events import AssistantMessage, UserMessage
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


class TestOpenCodeLikeSessionTranscriptRoute(unittest.TestCase):
    def test_transcript_route_returns_entries(self) -> None:
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
                created = _http(base + "/session", "POST", {})
                sid = created.get("id")
                self.assertIsInstance(sid, str)

                # Transcript should contain user/assistant messages, not tool payloads.
                store.append_event(sid, UserMessage(text="u"))
                store.append_event(sid, AssistantMessage(text="a"))

                tr = _http(base + f"/session/{sid}/transcript", "GET")
                self.assertEqual(tr.get("session_id"), sid)
                entries = tr.get("entries")
                self.assertIsInstance(entries, list)
                self.assertEqual([e.get("role") for e in entries if isinstance(e, dict)], ["user", "assistant"])
                self.assertEqual([e.get("text") for e in entries if isinstance(e, dict)], ["u", "a"])
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
