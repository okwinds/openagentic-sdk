import asyncio
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlencode, urlparse


class _ScopeServer:
    def __init__(self) -> None:
        self._srv: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._code_scope: dict[str, str] = {}

    @property
    def base_url(self) -> str:
        assert self._srv is not None
        host, port = self._srv.server_address[0], int(self._srv.server_address[1])
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
                            "registration_endpoint": parent.base_url + "/register",
                            "code_challenge_methods_supported": ["S256"],
                        },
                    )
                    return
                if u.path == "/authorize":
                    qs = parse_qs(u.query)
                    redirect_uri = (qs.get("redirect_uri") or [""])[0]
                    state = (qs.get("state") or [""])[0]
                    scope = (qs.get("scope") or [""])[0]
                    code = "code-stepup"
                    parent._code_scope[code] = scope
                    loc = redirect_uri + "?" + urlencode({"code": code, "state": state})
                    self.send_response(302)
                    self.send_header("Location", loc)
                    self.end_headers()
                    return
                self.send_response(404)
                self.end_headers()

            def do_POST(self):  # noqa: N802
                u = urlparse(self.path)
                n = int(self.headers.get("Content-Length") or "0")
                body = self.rfile.read(n) if n > 0 else b""
                if u.path == "/register":
                    _ = body
                    self._json(200, {"client_id": "cid1", "client_secret": "csecret1", "client_secret_expires_at": 0})
                    return
                if u.path == "/token":
                    qs = parse_qs(body.decode("utf-8", errors="replace"))
                    gt = (qs.get("grant_type") or [""])[0]
                    if gt != "authorization_code":
                        self._json(400, {"error": "unsupported_grant_type"})
                        return
                    code = (qs.get("code") or [""])[0]
                    scope = parent._code_scope.get(code) or ""
                    self._json(200, {"access_token": "tok-stepup", "expires_in": 3600, "token_type": "Bearer", "scope": scope})
                    return
                self.send_response(404)
                self.end_headers()

        self._srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._srv.daemon_threads = True
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        if self._srv is not None:
            self._srv.shutdown()
            self._srv.server_close()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._srv = None
        self._thread = None


class TestMcpOauthScopeStepUp(unittest.IsolatedAsyncioTestCase):
    async def test_reauth_when_required_scope_not_in_stored_scope(self) -> None:
        from openagentic_sdk.mcp.auth_store import McpAuthStore, McpClientInfo, McpTokens
        from openagentic_sdk.mcp.oauth_flow import McpOAuthManager

        srv = _ScopeServer()
        srv.start()
        try:
            with TemporaryDirectory() as td:
                root = Path(td)
                home = root / "oa-home"
                os.environ["OPENAGENTIC_SDK_HOME"] = str(home)
                try:
                    store = McpAuthStore.load_default()
                    store.update_client_info("srv", McpClientInfo(client_id="cid1", client_secret="csecret1"), server_url=srv.base_url + "/mcp")
                    store.update_tokens(
                        "srv",
                        McpTokens(access_token="tok-tools", refresh_token=None, expires_at=None, scope="mcp:tools"),
                        server_url=srv.base_url + "/mcp",
                    )
                    store.save()

                    mgr = McpOAuthManager(home=str(home), callback_port=0)
                    opened: list[str] = []

                    async def open_url(url: str) -> None:
                        opened.append(url)
                        import urllib.request

                        def _hit() -> None:
                            with urllib.request.urlopen(url) as _resp:  # noqa: S310
                                _resp.read(0)

                        await asyncio.to_thread(_hit)

                    tok = await mgr.authenticate(
                        server_key="srv",
                        server_url=srv.base_url + "/mcp",
                        scope="mcp:resources",
                        open_url=open_url,
                    )
                    self.assertEqual(tok, "tok-stepup")
                    self.assertTrue(opened)
                finally:
                    os.environ.pop("OPENAGENTIC_SDK_HOME", None)
        finally:
            srv.close()


if __name__ == "__main__":
    unittest.main()
