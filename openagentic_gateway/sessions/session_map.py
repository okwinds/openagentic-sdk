from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SessionMapRow:
    agent_id: str
    session_key: str
    session_id: str
    created_at: float
    updated_at: float


class SessionMap:
    def __init__(self, *, path: str) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_map (
              session_key TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              session_id TEXT NOT NULL,
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_session_map_agent_id ON session_map(agent_id)")
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def get_or_create(self, *, agent_id: str, session_key: str) -> str:
        key = (session_key or "").strip().lower()
        if not key:
            raise ValueError("session_key required")
        aid = (agent_id or "").strip().lower()
        now = time.time()

        with self._lock:
            cur = self._conn.execute("SELECT session_id FROM session_map WHERE session_key = ?", (key,))
            row = cur.fetchone()
            if row and isinstance(row[0], str) and row[0]:
                self._conn.execute("UPDATE session_map SET updated_at = ? WHERE session_key = ?", (now, key))
                self._conn.commit()
                return row[0]

            sid = uuid.uuid4().hex
            self._conn.execute(
                "INSERT INTO session_map(session_key, agent_id, session_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (key, aid, sid, now, now),
            )
            self._conn.commit()
            return sid

