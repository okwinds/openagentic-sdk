from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..paths import default_session_root


def _credentials_path() -> Path:
    # Keep everything under OPENAGENTIC_SDK_HOME for portability.
    return default_session_root() / "mcp" / "credentials.json"


@dataclass
class McpCredentialStore:
    path: Path
    _data: dict[str, Any]

    @classmethod
    def load_default(cls) -> "McpCredentialStore":
        return cls.load(_credentials_path())

    @classmethod
    def load(cls, path: Path) -> "McpCredentialStore":
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
            obj = json.loads(raw) if raw.strip() else {}
        except Exception:  # noqa: BLE001
            obj = {}
        if not isinstance(obj, dict):
            obj = {}
        return cls(path=path, _data=obj)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def set_bearer_token(self, server_key: str, token: str) -> None:
        if not server_key:
            raise ValueError("server_key must be non-empty")
        if not token:
            raise ValueError("token must be non-empty")
        rec = self._data.get(server_key)
        if not isinstance(rec, dict):
            rec = {}
        rec["bearer_token"] = token
        self._data[server_key] = rec

    def clear(self, server_key: str) -> None:
        self._data.pop(server_key, None)

    def bearer_token(self, server_key: str) -> str | None:
        rec = self._data.get(server_key)
        if not isinstance(rec, dict):
            return None
        tok = rec.get("bearer_token")
        return tok if isinstance(tok, str) and tok else None

    def merged_headers(self, server_key: str, base_headers: Mapping[str, str] | None) -> dict[str, str]:
        out = {str(k): str(v) for k, v in (base_headers or {}).items()}
        tok = self.bearer_token(server_key)
        if tok and "authorization" not in {k.lower() for k in out.keys()}:
            out["Authorization"] = f"Bearer {tok}"
        return out
