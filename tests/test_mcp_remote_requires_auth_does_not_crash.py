import asyncio
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from openagentic_sdk import query
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.sessions.store import FileSessionStore


class ProviderNoTools:
    name = "no-tools"

    async def complete(self, *, model: str, messages, tools=(), api_key=None):
        _ = (model, messages, tools, api_key)
        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 1}, raw=None)


class TestMcpRemoteRequiresAuthDoesNotCrash(unittest.IsolatedAsyncioTestCase):
    async def test_remote_mcp_401_is_non_fatal(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args):  # noqa: A002
                _ = (format, args)
                return

            def do_POST(self):  # noqa: N802
                u = urlparse(self.path)
                if u.path != "/mcp":
                    self.send_response(404)
                    self.end_headers()
                    return
                # Always require auth.
                self.send_response(401)
                self.send_header(
                    "WWW-Authenticate",
                    'Bearer realm="mcp", resource_metadata="http://127.0.0.1/.well-known/oauth-protected-resource", scope="mcp:tools"',
                )
                self.end_headers()

        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        httpd.daemon_threads = True
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        port = int(httpd.server_address[1])
        try:
            with TemporaryDirectory() as td:
                root = Path(td)
                store = FileSessionStore(root_dir=root)
                options = OpenAgenticOptions(
                    provider=ProviderNoTools(),
                    model="fake",
                    api_key="x",
                    cwd=str(root),
                    project_dir=str(root),
                    session_store=store,
                    permission_gate=PermissionGate(permission_mode="bypass"),
                    mcp_servers={"r": {"type": "remote", "url": f"http://127.0.0.1:{port}/mcp", "headers": {}}},
                )

                events = []
                async for e in query(prompt="hi", options=options):
                    events.append(e)
                # If MCP auth errors were fatal, query() would raise.
                self.assertTrue(any(getattr(e, "type", "") == "result" for e in events))
        finally:
            httpd.shutdown()
            httpd.server_close()
            await asyncio.to_thread(t.join, 1.0)


if __name__ == "__main__":
    unittest.main()
