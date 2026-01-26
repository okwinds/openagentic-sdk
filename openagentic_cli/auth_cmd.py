from __future__ import annotations

from openagentic_sdk.auth import ApiAuth, all_auth, remove_auth, set_auth


def cmd_auth_set(*, provider_id: str, key: str) -> str:
    pid = str(provider_id or "").strip()
    if not pid:
        raise ValueError("provider_id must be non-empty")
    k = str(key or "").strip()
    if not k:
        raise ValueError("key must be non-empty")
    set_auth(pid, ApiAuth(key=k))
    return f"Stored auth for {pid}."


def cmd_auth_remove(*, provider_id: str) -> str:
    pid = str(provider_id or "").strip()
    if not pid:
        raise ValueError("provider_id must be non-empty")
    remove_auth(pid)
    return f"Removed auth for {pid}."


def cmd_auth_list() -> str:
    ids = sorted(all_auth().keys())
    return "\n".join(ids)
