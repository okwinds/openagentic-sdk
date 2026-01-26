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
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.server.http_server import OpenAgenticHttpServer
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.tools.ask_user_question import AskUserQuestionTool
from openagentic_sdk.tools.bash import BashTool
from openagentic_sdk.tools.registry import ToolRegistry


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
    if not raw:
        return None
    return json.loads(raw.decode("utf-8", errors="replace"))


class ProviderNeedsPermission:
    name = "needs-permission"

    def __init__(self) -> None:
        self._n = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, messages, tools, api_key)
        self._n += 1
        if self._n == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall(tool_use_id="t1", name="Bash", arguments={"command": "pwd"})],
                usage={"total_tokens": 1},
                raw=None,
            )
        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 1}, raw=None)


class ProviderAsksQuestion:
    name = "asks-question"

    def __init__(self) -> None:
        self._n = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, messages, tools, api_key)
        self._n += 1
        if self._n == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[
                    ToolCall(
                        tool_use_id="q1",
                        name="AskUserQuestion",
                        arguments={"question": "pick", "options": ["A", "B"]},
                    )
                ],
                usage={"total_tokens": 1},
                raw=None,
            )
        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 1}, raw=None)


class TestServerPermissionAndQuestion(unittest.TestCase):
    def test_permission_queue_allows_tool_use(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            tools = ToolRegistry([BashTool(), AskUserQuestionTool()])

            opts = OpenAgenticOptions(
                provider=ProviderNeedsPermission(),
                model="m",
                api_key="x",
                cwd=str(root),
                project_dir=str(root),
                session_store=store,
                tools=tools,
                # Server should convert this to a remote-approval flow.
                permission_gate=PermissionGate(permission_mode="prompt", interactive=False),
            )

            server = OpenAgenticHttpServer(options=opts, host="127.0.0.1", port=0)
            httpd = server.serve_forever()
            port = int(httpd.server_address[1])
            th = threading.Thread(target=httpd.serve_forever, daemon=True)
            th.start()
            try:
                base = f"http://127.0.0.1:{port}"
                sid = _json_req(base + "/session", "POST", {}).get("id")

                # Kick off the prompt in a background thread; it should block on permissions.
                done: list[object] = []

                def _run() -> None:
                    done.append(_json_req(base + f"/session/{sid}/message", "POST", {"prompt": "hi"}))

                t = threading.Thread(target=_run, daemon=True)
                t.start()

                # Wait for permission request to appear.
                deadline = time.time() + 3.0
                req_id = None
                while time.time() < deadline:
                    lst = _json_req(base + "/permission", "GET")
                    if isinstance(lst, list) and lst:
                        req_id = lst[0].get("id")
                        break
                    time.sleep(0.05)
                self.assertIsInstance(req_id, str)

                _ = _json_req(base + f"/permission/{req_id}/reply", "POST", {"reply": "allow"})
                t.join(timeout=3.0)
                self.assertTrue(done)
            finally:
                httpd.shutdown()
                httpd.server_close()

    def test_question_queue_unblocks_ask_user_question(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            tools = ToolRegistry([AskUserQuestionTool()])

            opts = OpenAgenticOptions(
                provider=ProviderAsksQuestion(),
                model="m",
                api_key="x",
                cwd=str(root),
                project_dir=str(root),
                session_store=store,
                tools=tools,
                permission_gate=PermissionGate(permission_mode="bypass", interactive=False),
            )

            server = OpenAgenticHttpServer(options=opts, host="127.0.0.1", port=0)
            httpd = server.serve_forever()
            port = int(httpd.server_address[1])
            th = threading.Thread(target=httpd.serve_forever, daemon=True)
            th.start()
            try:
                base = f"http://127.0.0.1:{port}"
                sid = _json_req(base + "/session", "POST", {}).get("id")

                done: list[object] = []

                def _run() -> None:
                    done.append(_json_req(base + f"/session/{sid}/message", "POST", {"prompt": "hi"}))

                t = threading.Thread(target=_run, daemon=True)
                t.start()

                # Wait for question to appear.
                deadline = time.time() + 3.0
                qid = None
                while time.time() < deadline:
                    lst = _json_req(base + "/question", "GET")
                    if isinstance(lst, list) and lst:
                        qid = lst[0].get("id")
                        break
                    time.sleep(0.05)
                self.assertIsInstance(qid, str)

                _ = _json_req(base + f"/question/{qid}/reply", "POST", {"answers": ["A"]})
                t.join(timeout=3.0)
                self.assertTrue(done)
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
