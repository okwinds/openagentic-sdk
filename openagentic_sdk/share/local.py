from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..paths import default_session_root


def _default_share_dir() -> Path:
    return default_session_root() / "shares"


@dataclass(frozen=True, slots=True)
class LocalShareProvider:
    """Local, offline share provider.

    Stores shared session payloads under OPENAGENTIC_SDK_HOME.
    """

    root_dir: Path = _default_share_dir()

    def _path(self, share_id: str) -> Path:
        return self.root_dir / f"{share_id}.json"

    def share(self, payload: Mapping[str, Any]) -> str:
        share_id = uuid.uuid4().hex
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._path(share_id).write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return share_id

    def unshare(self, share_id: str) -> None:
        p = self._path(share_id)
        if p.exists():
            p.unlink()

    def fetch(self, share_id: str) -> dict[str, Any]:
        p = self._path(share_id)
        obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        if not isinstance(obj, dict):
            raise ValueError("shared payload must be object")
        return obj
