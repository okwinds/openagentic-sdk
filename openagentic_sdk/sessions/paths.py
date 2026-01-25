from __future__ import annotations

from pathlib import Path


def session_dir(root_dir: Path, session_id: str) -> Path:
    return root_dir / "sessions" / session_id


def events_path(root_dir: Path, session_id: str) -> Path:
    return session_dir(root_dir, session_id) / "events.jsonl"


def meta_path(root_dir: Path, session_id: str) -> Path:
    return session_dir(root_dir, session_id) / "meta.json"


def transcript_path(root_dir: Path, session_id: str) -> Path:
    return session_dir(root_dir, session_id) / "transcript.jsonl"
