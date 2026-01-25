import asyncio
import json
import os
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlparse


class _RefreshServer:
    def __init__(self) -> None:
        self.httpd: ThreadingHTTPServer | None = None
        self.t: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        assert self.httpd is not None
        host, port = self.httpd.server_address[0], int(self.httpd.server_address[1])
        return f"http://{host}:{port}"

    def start(self) -> None:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args):  # noqa: A002
                _ = (format, args)
                return

            def _json(self, code: int, obj: object) -> None:
                raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):  # noqa: N802
                u = urlparse(self.path)
                if u.path == "/.well-known/oauth-protected-resource":
                    self._json(200, {"resource": parent.base_url + "/mcp", "authorization_servers": [parent.base_url + "/issuer"]})
                    return
                if u.path == "/.well-known/oauth-authorization-server/issuer":
                    self._json(
                        200,
                        {
                            "issuer": parent.base_url + "/issuer",
                            "authorization_endpoint": parent.base_url + "/authorize",
                            "token_endpoint": parent.base_url + "/token",
                            "code_challenge_methods_supported": ["S256"],
                        },
                    )
                    return
                self.send_response(404)
                self.end_headers()

            def do_POST(self):  # noqa: N802
                u = urlparse(self.path)
                n = int(self.headers.get("Content-Length") or "0")
                body = self.rfile.read(n) if n > 0 else b""
                if u.path == "/token":
                    qs = parse_qs(body.decode("utf-8", errors="replace"))
                    gt = (qs.get("grant_type") or [""])[0]
                    if gt != "refresh_token":
                        self._json(400, {"error": "unsupported_grant_type"})
                        return
                    rt = (qs.get("refresh_token") or [""])[0]
                    if rt != "rt1":
                        self._json(400, {"error": "invalid_grant"})
                        return
                    self._json(200, {"access_token": "tok2", "refresh_token": "rt1", "expires_in": 3600, "token_type": "Bearer"})
                    return
                self.send_response(404)
                self.end_headers()

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.t.start()

    def close(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
        if self.t is not None and self.t.is_alive():
            self.t.join(timeout=1.0)
        self.httpd = None
        self.t = None


class TestMcpOauthRefresh(unittest.IsolatedAsyncioTestCase):
    async def test_refreshes_expired_token_without_opening_browser(self) -> None:
        from openagentic_sdk.mcp.auth_store import McpAuthStore, McpClientInfo, McpTokens
        from openagentic_sdk.mcp.oauth_flow import McpOAuthManager

        srv = _RefreshServer()
        srv.start()
        try:
            with TemporaryDirectory() as td:
                root = Path(td)
                home = root / "oa-home"
                os.environ["OPENAGENTIC_SDK_HOME"] = str(home)
                try:
                    store = McpAuthStore.load_default()
                    store.update_client_info("srv", McpClientInfo(client_id="cid1"), server_url=srv.base_url + "/mcp")
                    store.update_tokens(
                        "srv",
                        McpTokens(access_token="old", refresh_token="rt1", expires_at=time.time() - 10, scope=None),
                        server_url=srv.base_url + "/mcp",
                    )
                    store.save()

                    mgr = McpOAuthManager(home=str(home), callback_port=0)

                    async def open_url(_url: str) -> None:
                        raise AssertionError("should not open browser")

                    tok = await mgr.authenticate(server_key="srv", server_url=srv.base_url + "/mcp", scope=None, open_url=open_url)
                    self.assertEqual(tok, "tok2")
                finally:
                    os.environ.pop("OPENAGENTIC_SDK_HOME", None)
        finally:
            srv.close()


if __name__ == "__main__":
    unittest.main()
