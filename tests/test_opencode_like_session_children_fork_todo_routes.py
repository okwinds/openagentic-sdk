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


class TestOpenCodeLikeSessionChildrenForkTodoRoutes(unittest.TestCase):
    def test_children_and_fork_routes(self) -> None:
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
                parent = created.get("id")
                self.assertIsInstance(parent, str)

                # Create 2 user turns in the event log.
                store.append_event(parent, UserMessage(text="u1"))
                store.append_event(parent, AssistantMessage(text="a1"))
                store.append_event(parent, UserMessage(text="u2"))

                # Our OpenCode-like message ids are based on event seq.
                forked = _http(base + f"/session/{parent}/fork", "POST", {"messageID": "user_3"})
                child = forked.get("id")
                self.assertIsInstance(child, str)

                # Parent metadata should be present on the child session.
                md = forked.get("metadata") if isinstance(forked, dict) else None
                self.assertIsInstance(md, dict)
                self.assertEqual(md.get("parent_session_id"), parent)

                kids = _http(base + f"/session/{parent}/children", "GET")
                self.assertIsInstance(kids, list)
                kid_ids = [k.get("id") for k in kids if isinstance(k, dict)]
                self.assertIn(child, kid_ids)
            finally:
                httpd.shutdown()
                httpd.server_close()

    def test_todo_route_returns_opencode_shape(self) -> None:
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

                # Legacy on-disk todo shape (written today by TodoWrite).
                p = store.session_dir(sid) / "todos.json"
                p.write_text(
                    json.dumps(
                        {
                            "todos": [
                                {"content": "A", "activeForm": "Doing A", "status": "in_progress"},
                            ]
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                todos = _http(base + f"/session/{sid}/todo", "GET")
                self.assertIsInstance(todos, list)
                self.assertEqual(len(todos), 1)
                t0 = todos[0]
                self.assertIsInstance(t0, dict)
                self.assertEqual(t0.get("content"), "A")
                self.assertEqual(t0.get("status"), "in_progress")
                self.assertIn(t0.get("priority"), ("low", "medium", "high"))
                self.assertIsInstance(t0.get("id"), str)
                self.assertTrue(t0.get("id"))
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
