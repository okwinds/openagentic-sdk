from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .auth import GatewayAuthConfig, authorize_path
from .events import EventHub


@dataclass(frozen=True, slots=True)
class GatewayAddress:
    host: str
    port: int


class GatewayServer:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        agentcore_url: str | None = None,
        reply_engine: Any | None = None,
    ) -> None:
        self._host = host
        self._port = int(port)
        self._agentcore_url = (agentcore_url or "").strip() or None
        self._reply_engine = reply_engine
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._hub = EventHub()

    def start(self) -> GatewayAddress:
        if self._httpd is not None:
            raise RuntimeError("GatewayServer already started")

        auth_cfg = GatewayAuthConfig.from_env()

        class Handler(BaseHTTPRequestHandler):
            def _read_json(self) -> dict[str, Any] | None:
                try:
                    n = int(self.headers.get("Content-Length") or "0")
                except Exception:
                    n = 0
                if n <= 0 or n > 2_000_000:
                    return None
                raw = self.rfile.read(n)
                try:
                    obj = json.loads(raw.decode("utf-8", errors="replace"))
                except Exception:
                    return None
                return obj if isinstance(obj, dict) else None

            def do_GET(self) -> None:  # noqa: N802
                decision = authorize_path(path=self.path, headers=self.headers, cfg=auth_cfg)
                if not decision.allowed:
                    raw = json.dumps({"error": decision.error or "unauthorized"}, separators=(",", ":")).encode("utf-8")
                    self.send_response(int(decision.status))
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    return

                if self.path == "/health":
                    raw = json.dumps({"ok": True}, separators=(",", ":")).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    return

                if self.path == "/v1/gateway/status":
                    raw = json.dumps({"ok": True}, separators=(",", ":")).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    return

                if self.path == "/v1/events":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.end_headers()

                    q = self.server._hub.subscribe()  # type: ignore[attr-defined]
                    try:
                        self.wfile.write(b"data: {\"type\":\"gateway.connected\"}\n\n")
                        self.wfile.flush()
                        last_hb = time.time()
                        while True:
                            try:
                                obj = q.get(timeout=0.5)
                            except Exception:
                                obj = None
                            if obj is not None:
                                payload = json.dumps(obj, ensure_ascii=False)
                                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                                self.wfile.flush()
                            if time.time() - last_hb >= 30.0:
                                self.wfile.write(b"data: {\"type\":\"gateway.heartbeat\"}\n\n")
                                self.wfile.flush()
                                last_hb = time.time()
                    except (BrokenPipeError, ConnectionResetError):
                        return
                    finally:
                        try:
                            self.server._hub.unsubscribe(q)  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    return

                if self.path == "/permission":
                    base = getattr(self.server, "_agentcore_url", None)  # type: ignore[attr-defined]
                    if not isinstance(base, str) or not base:
                        self.send_response(404)
                        self.end_headers()
                        return
                    try:
                        req = Request(f"{base}/permission")
                        with urlopen(req, timeout=2.0) as resp:  # noqa: S310
                            data = resp.read()
                            self.send_response(resp.status)
                            for k, v in resp.headers.items():
                                if k.lower() in {"content-length", "connection", "transfer-encoding"}:
                                    continue
                                self.send_header(k, v)
                            self.send_header("Content-Length", str(len(data)))
                            self.end_headers()
                            self.wfile.write(data)
                            return
                    except HTTPError as e:
                        data = e.read() if getattr(e, "fp", None) is not None else b""
                        self.send_response(int(getattr(e, "code", 502) or 502))
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        if data:
                            self.wfile.write(data)
                        return
                    except Exception:
                        self.send_response(502)
                        self.end_headers()
                        return

                self.send_response(404)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(b'{"error":"not_found"}')

            def do_POST(self) -> None:  # noqa: N802
                decision = authorize_path(path=self.path, headers=self.headers, cfg=auth_cfg)
                if not decision.allowed:
                    raw = json.dumps({"error": decision.error or "unauthorized"}, separators=(",", ":")).encode("utf-8")
                    self.send_response(int(decision.status))
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    return

                if self.path == "/v1/chat/inbound":
                    engine = getattr(self.server, "_reply_engine", None)  # type: ignore[attr-defined]
                    if engine is None:
                        self.send_response(503)
                        self.end_headers()
                        return

                    obj = self._read_json()
                    if obj is None:
                        raw = b'{"error":"invalid_json"}'
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(raw)))
                        self.end_headers()
                        self.wfile.write(raw)
                        return

                    try:
                        from .reply.envelope import InboundEnvelope

                        env = InboundEnvelope(
                            channel=str(obj.get("channel") or ""),
                            account_id=str(obj.get("account_id") or ""),
                            peer_kind=str(obj.get("peer_kind") or ""),
                            peer_id=str(obj.get("peer_id") or ""),
                            text=str(obj.get("text") or ""),
                        )
                    except Exception:
                        raw = b'{"error":"invalid_request"}'
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(raw)))
                        self.end_headers()
                        self.wfile.write(raw)
                        return

                    try:
                        import asyncio

                        out = asyncio.run(engine.get_reply(env))
                        payloads = [{"kind": p.kind, "text": p.text} for p in out.payloads]
                        resp_obj = {"session_id": out.session_id, "payloads": payloads}
                        raw = json.dumps(resp_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(raw)))
                        self.end_headers()
                        self.wfile.write(raw)
                        return
                    except Exception:
                        raw = b'{"error":"internal_error"}'
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(raw)))
                        self.end_headers()
                        self.wfile.write(raw)
                        return

                if self.path.startswith("/v1/webhooks/telegram/"):
                    engine = getattr(self.server, "_reply_engine", None)  # type: ignore[attr-defined]
                    if engine is None:
                        self.send_response(503)
                        self.end_headers()
                        return

                    account_id = self.path.split("/v1/webhooks/telegram/", 1)[1].strip().strip("/")
                    if not account_id:
                        raw = b'{"error":"missing_account_id"}'
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(raw)))
                        self.end_headers()
                        self.wfile.write(raw)
                        return

                    obj = self._read_json()
                    if obj is None:
                        raw = b'{"error":"invalid_json"}'
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(raw)))
                        self.end_headers()
                        self.wfile.write(raw)
                        return

                    try:
                        from .channels.builtins.telegram_webhook import normalize_telegram_update

                        env = normalize_telegram_update(obj, account_id=account_id)
                        import asyncio

                        out = asyncio.run(engine.get_reply(env))
                        payloads = [{"kind": p.kind, "text": p.text} for p in out.payloads]
                        resp_obj = {"session_id": out.session_id, "payloads": payloads}
                        raw = json.dumps(resp_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(raw)))
                        self.end_headers()
                        self.wfile.write(raw)
                        return
                    except Exception:
                        raw = b'{"error":"internal_error"}'
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(raw)))
                        self.end_headers()
                        self.wfile.write(raw)
                        return

                self.send_response(404)
                self.end_headers()

            def log_message(self, _format: str, *_args: object) -> None:  # noqa: A002
                return

        httpd = ThreadingHTTPServer((self._host, self._port), Handler)
        httpd._hub = self._hub  # type: ignore[attr-defined]
        httpd._agentcore_url = self._agentcore_url  # type: ignore[attr-defined]
        httpd._reply_engine = self._reply_engine  # type: ignore[attr-defined]
        self._httpd = httpd
        addr = httpd.server_address
        host = str(addr[0])
        port = int(addr[1])

        t = threading.Thread(target=httpd.serve_forever, name=f"oa-gateway:{host}:{port}", daemon=True)
        self._thread = t
        t.start()
        return GatewayAddress(host=host, port=port)

    def close(self) -> None:
        httpd = self._httpd
        if httpd is None:
            return
        try:
            httpd.shutdown()
        finally:
            try:
                httpd.server_close()
            finally:
                self._httpd = None
