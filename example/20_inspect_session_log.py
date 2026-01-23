from __future__ import annotations

import argparse
import json
from pathlib import Path

from _common import default_session_root


def _pick_latest_session_id(sessions_dir: Path) -> str | None:
    best: tuple[float, str] | None = None
    for d in sessions_dir.iterdir() if sessions_dir.exists() else []:
        if not d.is_dir():
            continue
        meta = d / "meta.json"
        if not meta.exists():
            continue
        ts = meta.stat().st_mtime
        if best is None or ts > best[0]:
            best = (ts, d.name)
    return best[1] if best else None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("session_id", nargs="?", help="Session id to inspect (defaults to latest)")
    p.add_argument("--tail", type=int, default=30, help="How many events.jsonl lines to show")
    args = p.parse_args(argv)

    root = default_session_root()
    sessions_dir = root / "sessions"
    session_id = args.session_id or _pick_latest_session_id(sessions_dir)
    if not session_id:
        print(f"No sessions found under {sessions_dir}")
        print("Run any example that calls the SDK first (e.g. example/01_run_basic.py).")
        return 1

    meta_path = sessions_dir / session_id / "meta.json"
    events_path = sessions_dir / session_id / "events.jsonl"
    print(f"session_id={session_id}")
    print(f"meta_path={meta_path}")
    print(f"events_path={events_path}")

    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        print("--- meta.json ---")
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    else:
        print("(meta.json missing)")

    if events_path.exists():
        lines = events_path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-int(args.tail) :] if args.tail > 0 else []
        print(f"--- events.jsonl (tail {len(tail)}) ---")
        for ln in tail:
            print(ln)
    else:
        print("(events.jsonl missing)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

