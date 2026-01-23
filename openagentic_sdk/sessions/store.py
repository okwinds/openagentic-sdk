from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from ..events import Event
from ..serialization import event_to_dict, loads_event
from .paths import events_path, meta_path, session_dir


@dataclass(frozen=True, slots=True)
class FileSessionStore:
    root_dir: Path
    _seq: dict[str, int] = field(default_factory=dict, init=False, repr=False, compare=False)

    def create_session(self, *, metadata: Optional[dict[str, Any]] = None) -> str:
        session_id = uuid.uuid4().hex
        directory = self.session_dir(session_id)
        directory.mkdir(parents=True, exist_ok=False)

        meta = {
            "session_id": session_id,
            "created_at": time.time(),
            "metadata": metadata or {},
        }
        meta_file = meta_path(self.root_dir, session_id)
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        return session_id

    def session_dir(self, session_id: str) -> Path:
        return session_dir(self.root_dir, session_id)

    def append_event(self, session_id: str, event: Event) -> None:
        path = events_path(self.root_dir, session_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        seq = self._seq.get(session_id)
        if seq is None:
            seq = self._infer_next_seq(session_id)
        seq += 1
        self._seq[session_id] = seq

        obj = event_to_dict(event)
        obj["seq"] = seq
        obj["ts"] = time.time()

        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")

    def read_events(self, session_id: str) -> list[Event]:
        path = events_path(self.root_dir, session_id)
        if not path.exists():
            return []
        out: list[Event] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            out.append(loads_event(line))
        return out

    def append_events(self, session_id: str, events: Iterable[Event]) -> None:
        for e in events:
            self.append_event(session_id, e)

    def _infer_next_seq(self, session_id: str) -> int:
        path = events_path(self.root_dir, session_id)
        if not path.exists():
            return 0
        last_seq: int | None = None
        # Read from the end in a simple, safe way (small files expected for v0.1).
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                break
            if not isinstance(obj, dict):
                break
            seq = obj.get("seq")
            if isinstance(seq, int):
                last_seq = seq
                break
        if last_seq is not None:
            return last_seq
        # Back-compat: older logs without seq fields.
        return len([ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()])
