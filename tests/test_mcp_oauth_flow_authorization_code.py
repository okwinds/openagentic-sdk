import asyncio
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlencode, urlparse

import os


class _OAuthTestServer:
    def __init__(self) -> None:
        self._srv: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

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
                    # PRM -> points to issuer with path.
                    self._json(
                        200,
                        {
                            "resource": parent.base_url + "/mcp",
                            "authorization_servers": [parent.base_url + "/issuer"],
                            "scopes_supported": ["mcp:tools"],
                        },
                    )
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
                    code = "code1"
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
                    self._json(
                        200,
                        {
                            "client_id": "cid1",
                            "client_secret": "csecret1",
                            "client_secret_expires_at": 0,
                        },
                    )
                    return

                if u.path == "/token":
                    # Token endpoint is form-encoded.
                    qs = parse_qs(body.decode("utf-8", errors="replace"))
                    grant_type = (qs.get("grant_type") or [""])[0]
                    if grant_type != "authorization_code":
                        self._json(400, {"error": "unsupported_grant_type"})
                        return
                    code = (qs.get("code") or [""])[0]
                    if code != "code1":
                        self._json(400, {"error": "invalid_grant"})
                        return
                    self._json(
                        200,
                        {
                            "access_token": "tok1",
                            "refresh_token": "rt1",
                            "expires_in": 3600,
                            "token_type": "Bearer",
                            "scope": "mcp:tools",
                        },
                    )
                    return

                if u.path == "/mcp":
                    # MCP resource: first call without Authorization triggers 401 with PRM.
                    auth = self.headers.get("Authorization")
                    if not auth:
                        self.send_response(401)
                        self.send_header(
                            "WWW-Authenticate",
                            f'Bearer realm="mcp", resource_metadata="{parent.base_url}/.well-known/oauth-protected-resource", scope="mcp:tools"',
                        )
                        self.end_headers()
                        return
                    # Return minimal JSON-RPC success.
                    obj = json.loads(body.decode("utf-8", errors="replace"))
                    rid = obj.get("id")
                    self._json(200, {"jsonrpc": "2.0", "id": rid, "result": {"tools": []}})
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


class TestMcpOauthAuthorizationCodeFlow(unittest.IsolatedAsyncioTestCase):
    async def test_dynamic_registration_and_token_exchange(self) -> None:
        from openagentic_sdk.mcp.oauth_flow import McpOAuthManager

        with TemporaryDirectory() as td:
            root = Path(td)
            os_home = root / "oa-home"

            # Fake OAuth/MCP server.
            srv = _OAuthTestServer()
            srv.start()
            try:
                mgr = McpOAuthManager(home=str(os_home), callback_port=0)

                async def open_url(url: str) -> None:
                    # Simulate browser by requesting the authorization URL (follows redirect).
                    import urllib.request

                    def _hit() -> None:
                        with urllib.request.urlopen(url) as _resp:  # noqa: S310
                            _resp.read(0)

                    await asyncio.to_thread(_hit)

                token = await mgr.authenticate(server_key="srv", server_url=srv.base_url + "/mcp", scope="mcp:tools", open_url=open_url)
                self.assertEqual(token, "tok1")

                entry = mgr.auth_store.get_for_url("srv", server_url=srv.base_url + "/mcp")
                self.assertIsNotNone(entry)
                assert entry is not None
                self.assertIsNotNone(entry.tokens)
                assert entry.tokens is not None
                self.assertEqual(entry.tokens.access_token, "tok1")
            finally:
                srv.close()


if __name__ == "__main__":
    unittest.main()
