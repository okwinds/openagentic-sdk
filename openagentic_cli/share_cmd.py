from __future__ import annotations

import json
from pathlib import Path

from openagentic_sdk.paths import default_session_root
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.share.share import fetch_shared_session, share_session, unshare_session


def cmd_share(*, session_id: str, session_root: str | None = None) -> str:
    root = Path(session_root).expanduser() if session_root else default_session_root()
    store = FileSessionStore(root_dir=root)
    share_id = share_session(store=store, session_id=session_id)
    return share_id


def cmd_unshare(*, share_id: str) -> str:
    unshare_session(share_id=share_id)
    return "ok"


def cmd_shared(*, share_id: str) -> str:
    shared = fetch_shared_session(share_id=share_id)
    return json.dumps(shared.payload, ensure_ascii=False, indent=2)
