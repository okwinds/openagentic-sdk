from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, replace
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

from ..api import run
from ..options import OpenAgenticOptions
from ..serialization import event_to_dict
from ..sessions.rebuild import rebuild_messages
from ..sessions.store import FileSessionStore


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    obj = json.loads(raw.decode("utf-8", errors="replace"))
    return obj if isinstance(obj, dict) else {}


def _write_json(handler: BaseHTTPRequestHandler, status: int, obj: Any) -> None:
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def _split_path(path: str) -> list[str]:
    return [p for p in (path or "").split("?")[0].split("/") if p]


@dataclass(frozen=True, slots=True)
class OpenAgenticHttpServer:
    options: OpenAgenticOptions
    host: str = "127.0.0.1"
    port: int = 0

    def serve_forever(self) -> ThreadingHTTPServer:
        store = self.options.session_store
        if store is None:
            root = self.options.session_root or Path.home() / ".openagentic-sdk"
            store = FileSessionStore(root_dir=root)

        opts = self.options

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                parts = _split_path(self.path)
                if parts == ["health"]:
                    _write_json(self, 200, {"ok": True})
                    return

                if parts == ["session"]:
                    _write_json(self, 200, {"sessions": list_sessions(store)})
                    return

                if len(parts) >= 2 and parts[0] == "session":
                    sid = parts[1]
                    if len(parts) == 2:
                        _write_json(self, 200, {"session_id": sid, "metadata": store.read_metadata(sid)})
                        return
                    if len(parts) == 3 and parts[2] == "events":
                        evs = store.read_events(sid)
                        _write_json(self, 200, {"session_id": sid, "events": [event_to_dict(e) for e in evs]})
                        return
                    if len(parts) == 3 and parts[2] == "message":
                        evs = store.read_events(sid)
                        msgs = rebuild_messages(evs, max_events=1000, max_bytes=2_000_000)
                        _write_json(self, 200, {"session_id": sid, "messages": msgs})
                        return

                _write_json(self, 404, {"error": "not_found"})

            def do_POST(self):  # noqa: N802
                parts = _split_path(self.path)
                if parts == ["session"]:
                    sid = store.create_session(metadata={})
                    _write_json(self, 200, {"session_id": sid})
                    return

                if len(parts) == 3 and parts[0] == "session" and parts[2] == "message":
                    sid = parts[1]
                    body = _read_json(self)
                    prompt = body.get("prompt") or body.get("content") or body.get("text")
                    if not isinstance(prompt, str) or not prompt:
                        _write_json(self, 400, {"error": "invalid_prompt"})
                        return

                    # Run a single prompt against the existing session.
                    opts2 = replace(opts, resume=sid, session_store=store)
                    rr = asyncio.run(run(prompt=prompt, options=opts2))
                    _write_json(self, 200, {"session_id": sid, "final_text": rr.final_text})
                    return

                _write_json(self, 404, {"error": "not_found"})

            def log_message(self, fmt, *args):  # noqa: ANN001
                return

        httpd = ThreadingHTTPServer((self.host, int(self.port)), Handler)
        return httpd


def list_sessions(store: FileSessionStore) -> list[dict[str, Any]]:
    root = store.root_dir / "sessions"
    if not root.exists():
        return []
    out: list[dict[str, Any]] = []
    for d in root.iterdir():
        if not d.is_dir():
            continue
        meta = d / "meta.json"
        if not meta.exists():
            continue
        try:
            obj = json.loads(meta.read_text(encoding="utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(obj, dict):
            continue
        sid = obj.get("session_id")
        if isinstance(sid, str) and sid:
            out.append({"session_id": sid, "metadata": obj.get("metadata") or {}})
    return out


def serve_http(*, options: OpenAgenticOptions, host: str = "127.0.0.1", port: int = 0) -> None:
    server = OpenAgenticHttpServer(options=options, host=host, port=port)
    httpd = server.serve_forever()
    httpd.serve_forever()
