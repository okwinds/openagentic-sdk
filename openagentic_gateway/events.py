from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GatewayEvent:
    type: str
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, **(self.data or {})}


class EventHub:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: list["queue.Queue[dict[str, Any]]"] = []

    def subscribe(self) -> "queue.Queue[dict[str, Any]]":
        q: "queue.Queue[dict[str, Any]]" = queue.Queue()
        with self._lock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q: "queue.Queue[dict[str, Any]]") -> None:
        with self._lock:
            try:
                self._subs.remove(q)
            except ValueError:
                return

    def publish(self, obj: dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(obj)
            except Exception:
                continue

