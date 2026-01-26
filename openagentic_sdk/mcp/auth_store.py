from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..paths import default_session_root


def _default_path() -> Path:
    # Keep everything under OPENAGENTIC_SDK_HOME for portability, but match
    # OpenCode's filename to ease manual inspection/migration.
    return default_session_root() / "mcp" / "mcp-auth.json"


def _chmod_0600(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except Exception:  # noqa: BLE001
        # Best-effort (e.g., Windows).
        pass


@dataclass(frozen=True, slots=True)
class McpTokens:
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None
    scope: str | None = None


@dataclass(frozen=True, slots=True)
class McpClientInfo:
    client_id: str
    client_secret: str | None = None
    client_id_issued_at: float | None = None
    client_secret_expires_at: float | None = None


@dataclass(frozen=True, slots=True)
class McpAuthEntry:
    tokens: McpTokens | None = None
    client_info: McpClientInfo | None = None
    code_verifier: str | None = None
    oauth_state: str | None = None
    server_url: str | None = None


def _entry_from_obj(obj: Any) -> McpAuthEntry:
    if not isinstance(obj, dict):
        return McpAuthEntry()

    tokens_obj = obj.get("tokens")
    tokens: McpTokens | None = None
    if isinstance(tokens_obj, dict):
        at = tokens_obj.get("accessToken") or tokens_obj.get("access_token")
        if isinstance(at, str) and at:
            tokens = McpTokens(
                access_token=at,
                refresh_token=tokens_obj.get("refreshToken") if isinstance(tokens_obj.get("refreshToken"), str) else None,
                expires_at=float(tokens_obj.get("expiresAt")) if isinstance(tokens_obj.get("expiresAt"), (int, float)) else None,
                scope=tokens_obj.get("scope") if isinstance(tokens_obj.get("scope"), str) else None,
            )

    ci_obj = obj.get("clientInfo")
    client_info: McpClientInfo | None = None
    if isinstance(ci_obj, dict):
        cid = ci_obj.get("clientId")
        if isinstance(cid, str) and cid:
            client_info = McpClientInfo(
                client_id=cid,
                client_secret=ci_obj.get("clientSecret") if isinstance(ci_obj.get("clientSecret"), str) else None,
                client_id_issued_at=float(ci_obj.get("clientIdIssuedAt"))
                if isinstance(ci_obj.get("clientIdIssuedAt"), (int, float))
                else None,
                client_secret_expires_at=float(ci_obj.get("clientSecretExpiresAt"))
                if isinstance(ci_obj.get("clientSecretExpiresAt"), (int, float))
                else None,
            )

    return McpAuthEntry(
        tokens=tokens,
        client_info=client_info,
        code_verifier=obj.get("codeVerifier") if isinstance(obj.get("codeVerifier"), str) else None,
        oauth_state=obj.get("oauthState") if isinstance(obj.get("oauthState"), str) else None,
        server_url=obj.get("serverUrl") if isinstance(obj.get("serverUrl"), str) else None,
    )


def _entry_to_obj(entry: McpAuthEntry) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if entry.tokens is not None:
        out["tokens"] = {
            "accessToken": entry.tokens.access_token,
            "refreshToken": entry.tokens.refresh_token,
            "expiresAt": entry.tokens.expires_at,
            "scope": entry.tokens.scope,
        }
    if entry.client_info is not None:
        out["clientInfo"] = {
            "clientId": entry.client_info.client_id,
            "clientSecret": entry.client_info.client_secret,
            "clientIdIssuedAt": entry.client_info.client_id_issued_at,
            "clientSecretExpiresAt": entry.client_info.client_secret_expires_at,
        }
    if entry.code_verifier:
        out["codeVerifier"] = entry.code_verifier
    if entry.oauth_state:
        out["oauthState"] = entry.oauth_state
    if entry.server_url:
        out["serverUrl"] = entry.server_url
    return out


@dataclass
class McpAuthStore:
    path: Path
    _data: dict[str, Any]

    @classmethod
    def load_default(cls) -> "McpAuthStore":
        return cls.load(_default_path())

    @classmethod
    def load(cls, path: Path) -> "McpAuthStore":
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
        _chmod_0600(self.path)

    def get(self, server_key: str) -> McpAuthEntry | None:
        if not server_key:
            return None
        obj = self._data.get(server_key)
        if not isinstance(obj, dict):
            return None
        return _entry_from_obj(obj)

    def get_for_url(self, server_key: str, *, server_url: str) -> McpAuthEntry | None:
        entry = self.get(server_key)
        if entry is None:
            return None
        if not entry.server_url or entry.server_url != server_url:
            return None
        return entry

    def set(self, server_key: str, entry: McpAuthEntry) -> None:
        if not server_key:
            raise ValueError("server_key must be non-empty")
        self._data[server_key] = _entry_to_obj(entry)

    def remove(self, server_key: str) -> None:
        self._data.pop(server_key, None)

    def update_tokens(self, server_key: str, tokens: McpTokens, *, server_url: str | None = None) -> None:
        cur = self.get(server_key) or McpAuthEntry()
        self.set(
            server_key,
            McpAuthEntry(
                tokens=tokens,
                client_info=cur.client_info,
                code_verifier=cur.code_verifier,
                oauth_state=cur.oauth_state,
                server_url=server_url or cur.server_url,
            ),
        )

    def update_client_info(self, server_key: str, client_info: McpClientInfo, *, server_url: str | None = None) -> None:
        cur = self.get(server_key) or McpAuthEntry()
        self.set(
            server_key,
            McpAuthEntry(
                tokens=cur.tokens,
                client_info=client_info,
                code_verifier=cur.code_verifier,
                oauth_state=cur.oauth_state,
                server_url=server_url or cur.server_url,
            ),
        )

    def update_code_verifier(self, server_key: str, code_verifier: str) -> None:
        cur = self.get(server_key) or McpAuthEntry()
        self.set(
            server_key,
            McpAuthEntry(
                tokens=cur.tokens,
                client_info=cur.client_info,
                code_verifier=str(code_verifier),
                oauth_state=cur.oauth_state,
                server_url=cur.server_url,
            ),
        )

    def clear_code_verifier(self, server_key: str) -> None:
        cur = self.get(server_key) or McpAuthEntry()
        self.set(
            server_key,
            McpAuthEntry(
                tokens=cur.tokens,
                client_info=cur.client_info,
                code_verifier=None,
                oauth_state=cur.oauth_state,
                server_url=cur.server_url,
            ),
        )

    def update_oauth_state(self, server_key: str, oauth_state: str) -> None:
        cur = self.get(server_key) or McpAuthEntry()
        self.set(
            server_key,
            McpAuthEntry(
                tokens=cur.tokens,
                client_info=cur.client_info,
                code_verifier=cur.code_verifier,
                oauth_state=str(oauth_state),
                server_url=cur.server_url,
            ),
        )

    def clear_oauth_state(self, server_key: str) -> None:
        cur = self.get(server_key) or McpAuthEntry()
        self.set(
            server_key,
            McpAuthEntry(
                tokens=cur.tokens,
                client_info=cur.client_info,
                code_verifier=cur.code_verifier,
                oauth_state=None,
                server_url=cur.server_url,
            ),
        )

    def is_token_expired(self, server_key: str) -> bool | None:
        entry = self.get(server_key)
        if entry is None or entry.tokens is None:
            return None
        if entry.tokens.expires_at is None:
            return False
        return float(entry.tokens.expires_at) < time.time()
