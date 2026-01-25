from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any


def _request_json(url: str, *, method: str, payload: dict | None = None, timeout_s: float = 10.0) -> dict[str, Any]:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=float(timeout_s)) as resp:
        raw = resp.read()
    obj = json.loads(raw.decode("utf-8", errors="replace"))
    return obj if isinstance(obj, dict) else {}


def _request_json_any(url: str, *, method: str, payload: dict | None = None, timeout_s: float = 10.0) -> Any:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=float(timeout_s)) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace"))


@dataclass(frozen=True, slots=True)
class OpenAgenticHttpClient:
    base_url: str
    timeout_s: float = 10.0

    def health(self) -> dict[str, Any]:
        return _request_json(self.base_url.rstrip("/") + "/health", method="GET", timeout_s=self.timeout_s)

    def list_sessions(self) -> dict[str, Any]:
        obj = _request_json_any(self.base_url.rstrip("/") + "/session", method="GET", timeout_s=self.timeout_s)
        return {"sessions": obj} if isinstance(obj, list) else {"sessions": []}

    def create_session(self) -> str:
        obj = _request_json(self.base_url.rstrip("/") + "/session", method="POST", payload={}, timeout_s=self.timeout_s)
        sid = obj.get("id")
        if not isinstance(sid, str) or not sid:
            raise RuntimeError("server did not return session_id")
        return sid

    def send_message(self, *, session_id: str, prompt: str) -> str:
        obj = _request_json(
            self.base_url.rstrip("/") + f"/session/{session_id}/message",
            method="POST",
            payload={"prompt": prompt},
            timeout_s=self.timeout_s,
        )
        parts = obj.get("parts") if isinstance(obj, dict) else None
        if isinstance(parts, list):
            for p in parts:
                if isinstance(p, dict) and p.get("type") == "text" and isinstance(p.get("text"), str):
                    return str(p.get("text"))
        raise RuntimeError("server did not return assistant text")

    def get_events(self, *, session_id: str) -> dict[str, Any]:
        return _request_json(self.base_url.rstrip("/") + f"/session/{session_id}/events", method="GET", timeout_s=self.timeout_s)
