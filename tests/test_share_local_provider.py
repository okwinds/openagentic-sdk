from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from openagentic_sdk.events import AssistantMessage, UserMessage
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.share.local import LocalShareProvider
from openagentic_sdk.share.share import fetch_shared_session, share_session, unshare_session


class TestShareLocalProvider(unittest.TestCase):
    def test_share_unshare_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ["OPENAGENTIC_SDK_HOME"] = td
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session(metadata={"k": "v"})
            store.append_event(sid, UserMessage(text="u"))
            store.append_event(sid, AssistantMessage(text="a"))

            provider = LocalShareProvider(root_dir=root / "shares")
            share_id = share_session(store=store, session_id=sid, provider=provider)
            shared = fetch_shared_session(share_id=share_id, provider=provider)
            self.assertEqual(shared.payload.get("session_id"), sid)
            self.assertIsInstance(shared.payload.get("events"), list)

            unshare_session(share_id=share_id, provider=provider)
            self.assertFalse((root / "shares" / f"{share_id}.json").exists())


if __name__ == "__main__":
    unittest.main()
