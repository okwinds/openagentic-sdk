from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .paths import default_session_root


def _auth_path() -> Path:
    return default_session_root() / "auth.json"


@dataclass(frozen=True, slots=True)
class OAuthAuth:
    type: Literal["oauth"] = "oauth"
    refresh: str = ""
    access: str = ""
    expires: int = 0
    accountId: str | None = None
    enterpriseUrl: str | None = None


@dataclass(frozen=True, slots=True)
class ApiAuth:
    type: Literal["api"] = "api"
    key: str = ""


@dataclass(frozen=True, slots=True)
class WellKnownAuth:
    type: Literal["wellknown"] = "wellknown"
    key: str = ""
    token: str = ""


AuthInfo = OAuthAuth | ApiAuth | WellKnownAuth


def _parse_auth_info(obj: Any) -> AuthInfo | None:
    if not isinstance(obj, dict):
        return None
    typ = obj.get("type")
    if typ == "oauth":
        refresh = obj.get("refresh")
        access = obj.get("access")
        expires = obj.get("expires")
        if not isinstance(refresh, str) or not isinstance(access, str) or not isinstance(expires, int):
            return None
        return OAuthAuth(
            refresh=refresh,
            access=access,
            expires=expires,
            accountId=obj.get("accountId") if isinstance(obj.get("accountId"), str) else None,
            enterpriseUrl=obj.get("enterpriseUrl") if isinstance(obj.get("enterpriseUrl"), str) else None,
        )
    if typ == "api":
        key = obj.get("key")
        if not isinstance(key, str):
            return None
        return ApiAuth(key=key)
    if typ == "wellknown":
        k = obj.get("key")
        token = obj.get("token")
        if not isinstance(k, str) or not isinstance(token, str):
            return None
        return WellKnownAuth(key=k, token=token)
    return None


def all_auth(*, path: Path | None = None) -> dict[str, AuthInfo]:
    p = path or _auth_path()
    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
        obj = json.loads(raw) if raw.strip() else {}
    except Exception:  # noqa: BLE001
        obj = {}
    if not isinstance(obj, dict):
        return {}
    out: dict[str, AuthInfo] = {}
    for k, v in obj.items():
        if not isinstance(k, str) or not k:
            continue
        parsed = _parse_auth_info(v)
        if parsed is not None:
            out[k] = parsed
    return out


def set_auth(provider_id: str, info: AuthInfo, *, path: Path | None = None) -> None:
    if not provider_id:
        raise ValueError("provider_id must be non-empty")
    p = path or _auth_path()
    data: dict[str, Any] = {k: asdict(v) for k, v in all_auth(path=p).items()}
    data[provider_id] = asdict(info)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except Exception:  # noqa: BLE001
        pass


def remove_auth(provider_id: str, *, path: Path | None = None) -> None:
    p = path or _auth_path()
    data: dict[str, Any] = {k: asdict(v) for k, v in all_auth(path=p).items()}
    data.pop(provider_id, None)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except Exception:  # noqa: BLE001
        pass
