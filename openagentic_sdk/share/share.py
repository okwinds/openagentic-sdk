from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from ..serialization import event_to_dict
from ..sessions.store import FileSessionStore
from .local import LocalShareProvider


class ShareProvider(Protocol):
    def share(self, payload: Mapping[str, Any]) -> str:
        ...

    def unshare(self, share_id: str) -> None:
        ...

    def fetch(self, share_id: str) -> dict[str, Any]:
        ...


@dataclass(frozen=True, slots=True)
class SharedSession:
    share_id: str
    payload: dict[str, Any]


def share_session(*, store: FileSessionStore, session_id: str, provider: ShareProvider | None = None) -> str:
    provider2: ShareProvider = provider or LocalShareProvider()
    meta = store.read_metadata(session_id)
    events = store.read_events(session_id)

    # Redact tool payloads by default: shares are meant for viewing conversation,
    # not leaking filesystem contents or credentials.
    redacted_events: list[dict[str, Any]] = []
    for e in events:
        d = event_to_dict(e)
        if not isinstance(d, dict):
            continue
        if d.get("type") == "tool.use" and "input" in d:
            d = dict(d)
            d["input"] = {}
        if d.get("type") == "tool.result" and "output" in d:
            d = dict(d)
            d["output"] = None
        redacted_events.append(d)

    transcript_entries: list[dict[str, Any]] = []
    try:
        tp = store.session_dir(session_id) / "transcript.jsonl"
        if tp.exists():
            for line in tp.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    transcript_entries.append(obj)
    except Exception:
        transcript_entries = []

    payload = {
        "session_id": session_id,
        "metadata": meta,
        "events": redacted_events,
        "transcript": transcript_entries,
    }
    return provider2.share(payload)


def unshare_session(*, share_id: str, provider: ShareProvider | None = None) -> None:
    provider2: ShareProvider = provider or LocalShareProvider()
    provider2.unshare(share_id)


def fetch_shared_session(*, share_id: str, provider: ShareProvider | None = None) -> SharedSession:
    provider2: ShareProvider = provider or LocalShareProvider()
    payload = provider2.fetch(share_id)
    return SharedSession(share_id=share_id, payload=payload)
