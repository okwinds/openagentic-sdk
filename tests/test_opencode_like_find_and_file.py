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


def _json_req(url: str):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
        raw = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace"))


class TestOpenCodeLikeFindAndFile(unittest.TestCase):
    def test_file_tree_and_content_and_find(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("hello needle\n", encoding="utf-8")
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
                nodes = _json_req(base + "/file?path=")
                self.assertTrue(any(isinstance(n, dict) and n.get("name") == "a.txt" for n in nodes))

                content = _json_req(base + "/file/content?path=a.txt")
                self.assertIn("needle", content.get("content", ""))

                found = _json_req(base + "/find?pattern=needle")
                self.assertIsInstance(found, list)

                files = _json_req(base + "/find/file?query=a.txt")
                self.assertTrue(any("a.txt" in x for x in files))
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
