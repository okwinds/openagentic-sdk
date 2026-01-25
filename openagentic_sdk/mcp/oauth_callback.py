from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


@dataclass
class OAuthCallbackServer:
    """Local loopback OAuth callback server.

    OpenCode uses a fixed port/path (`127.0.0.1:19876/mcp/oauth/callback`).
    For tests we allow `port=0` (ephemeral).
    """

    host: str = "127.0.0.1"
    port: int = 19876
    path: str = "/mcp/oauth/callback"

    _srv: ThreadingHTTPServer | None = None
    _thread: threading.Thread | None = None
    _loop: asyncio.AbstractEventLoop | None = None
    _pending: dict[str, asyncio.Future[str]] = field(default_factory=dict)

    @property
    def redirect_uri(self) -> str:
        s = self._srv
        port = self.port
        if s is not None:
            try:
                port = int(s.server_address[1])
            except Exception:  # noqa: BLE001
                port = self.port
        return f"http://{self.host}:{port}{self.path}"

    async def start(self) -> None:
        if self._srv is not None:
            return
        self._loop = asyncio.get_running_loop()

        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002,ANN401
                # Never log to stderr (and never log secrets).
                _ = (format, args)
                return

            def do_GET(self) -> None:  # noqa: N802
                u = urlparse(self.path)
                if u.path != parent.path:
                    self.send_response(404)
                    self.end_headers()
                    return

                qs = parse_qs(u.query)
                state = (qs.get("state") or [""])[0]
                code = (qs.get("code") or [""])[0]
                err = (qs.get("error") or [""])[0]
                err_desc = (qs.get("error_description") or [""])[0]

                if not state:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing required state parameter")
                    return

                fut = parent._pending.get(state)
                if fut is None:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Invalid or expired state parameter")
                    return

                # Resolve promise (thread-safe via loop).
                parent._pending.pop(state, None)
                loop = parent._loop
                if loop is not None and not fut.done():
                    if err:
                        msg = err_desc or err
                        loop.call_soon_threadsafe(fut.set_exception, RuntimeError(msg))
                    else:
                        loop.call_soon_threadsafe(fut.set_result, code)

                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OAuth complete. You may close this window.")

        srv = ThreadingHTTPServer((self.host, self.port), Handler)
        srv.daemon_threads = True
        self._srv = srv
        # Update port in case of ephemeral.
        self.port = int(srv.server_address[1])

        def _run() -> None:
            try:
                srv.serve_forever(poll_interval=0.25)
            except Exception:
                return

        t = threading.Thread(target=_run, name="oa-mcp-oauth-callback", daemon=True)
        self._thread = t
        t.start()

    async def close(self) -> None:
        srv = self._srv
        self._srv = None
        if srv is not None:
            try:
                srv.shutdown()
            except Exception:  # noqa: BLE001
                pass
            try:
                srv.server_close()
            except Exception:  # noqa: BLE001
                pass

        t = self._thread
        self._thread = None
        if t is not None and t.is_alive():
            await asyncio.to_thread(t.join, 1.0)

        # Fail any pending waiters.
        for state, fut in list(self._pending.items()):
            if not fut.done():
                fut.set_exception(RuntimeError("oauth callback server closed"))
        self._pending.clear()

    async def wait_for_callback(self, state: str, *, timeout_s: float = 300.0) -> str:
        if not state:
            raise ValueError("state must be non-empty")
        await self.start()

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[str] = loop.create_future()
        if state in self._pending:
            raise RuntimeError("callback already pending for state")
        self._pending[state] = fut

        def _timeout() -> None:
            if fut.done():
                return
            self._pending.pop(state, None)
            fut.set_exception(TimeoutError("oauth callback timeout"))

        h = loop.call_later(float(timeout_s), _timeout)
        try:
            return await fut
        finally:
            h.cancel()
