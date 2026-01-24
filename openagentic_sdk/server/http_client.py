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


@dataclass(frozen=True, slots=True)
class OpenAgenticHttpClient:
    base_url: str
    timeout_s: float = 10.0

    def health(self) -> dict[str, Any]:
        return _request_json(self.base_url.rstrip("/") + "/health", method="GET", timeout_s=self.timeout_s)

    def list_sessions(self) -> dict[str, Any]:
        return _request_json(self.base_url.rstrip("/") + "/session", method="GET", timeout_s=self.timeout_s)

    def create_session(self) -> str:
        obj = _request_json(self.base_url.rstrip("/") + "/session", method="POST", payload={}, timeout_s=self.timeout_s)
        sid = obj.get("session_id")
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
        text = obj.get("final_text")
        if not isinstance(text, str):
            raise RuntimeError("server did not return final_text")
        return text

    def get_events(self, *, session_id: str) -> dict[str, Any]:
        return _request_json(self.base_url.rstrip("/") + f"/session/{session_id}/events", method="GET", timeout_s=self.timeout_s)
