from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from ..paths import default_session_root


def _env_flag(name: str) -> bool:
    v = os.environ.get(name)
    if v is None:
        return False
    if v == "":
        return True
    return str(v).strip().lower() not in {"0", "false", "no", "off"}


def _cache_path() -> Path:
    return default_session_root() / "cache" / "models.json"


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None
    except Exception:  # noqa: BLE001
        return None
    try:
        obj = json.loads(raw) if raw.strip() else {}
    except Exception:  # noqa: BLE001
        return None
    return obj if isinstance(obj, dict) else None


def _write_json_file(path: Path, obj: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(obj), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fetch_models_dev(url_base: str, *, timeout_s: float = 10.0, max_bytes: int = 10_000_000) -> dict[str, Any] | None:
    base = str(url_base or "").strip()
    u = urlparse(base)
    if u.scheme not in ("http", "https"):
        return None
    if not u.netloc:
        return None
    url = base.rstrip("/") + "/api.json"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=float(timeout_s)) as resp:  # noqa: S310
            raw = resp.read(max_bytes + 1)
    except Exception:  # noqa: BLE001
        return None
    if len(raw) > max_bytes:
        return None
    try:
        obj = json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001
        return None
    return obj if isinstance(obj, dict) else None


def get_models_dev() -> dict[str, Any]:
    """Return models.dev provider database.

    OpenCode load order:
    - cached models.json
    - optional build snapshot
    - fetch from models.dev/api.json (unless disabled)

    This function avoids background side effects; callers can call refresh.
    """

    cache_path = _cache_path()
    cached = _read_json_file(cache_path)
    if cached is not None:
        return cached

    # Optional embedded snapshot (may not exist in dev installs).
    try:
        from . import models_dev_snapshot as snapshot_mod  # type: ignore

        snap = getattr(snapshot_mod, "SNAPSHOT", None)
        if isinstance(snap, dict):
            return dict(snap)
    except Exception:  # noqa: BLE001
        pass

    if _env_flag("OPENCODE_DISABLE_MODELS_FETCH"):
        return {}

    base = os.environ.get("OPENCODE_MODELS_URL") or "https://models.dev"
    fetched = _fetch_models_dev(base)
    if fetched is None:
        return {}
    try:
        _write_json_file(cache_path, fetched)
    except Exception:  # noqa: BLE001
        pass
    return fetched


def refresh_models_dev() -> bool:
    """Force refresh the models.dev cache (best-effort).

    Returns True if new data was fetched and written.
    """

    if _env_flag("OPENCODE_DISABLE_MODELS_FETCH"):
        return False
    base = os.environ.get("OPENCODE_MODELS_URL") or "https://models.dev"
    fetched = _fetch_models_dev(base)
    if fetched is None:
        return False
    _write_json_file(_cache_path(), fetched)
    return True
