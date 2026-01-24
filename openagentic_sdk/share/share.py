from __future__ import annotations

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
    payload = {
        "session_id": session_id,
        "metadata": meta,
        "events": [event_to_dict(e) for e in events],
    }
    return provider2.share(payload)


def unshare_session(*, share_id: str, provider: ShareProvider | None = None) -> None:
    provider2: ShareProvider = provider or LocalShareProvider()
    provider2.unshare(share_id)


def fetch_shared_session(*, share_id: str, provider: ShareProvider | None = None) -> SharedSession:
    provider2: ShareProvider = provider or LocalShareProvider()
    payload = provider2.fetch(share_id)
    return SharedSession(share_id=share_id, payload=payload)
