from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.events import AssistantMessage, UserMessage
from openagentic_sdk.sessions.rebuild import rebuild_messages
from openagentic_sdk.sessions.store import FileSessionStore


class TestSessionRevertUndoRedo(unittest.TestCase):
    def test_set_head_undo_redo_filters_rebuild(self) -> None:
        with TemporaryDirectory() as td:
            store = FileSessionStore(root_dir=Path(td))
            sid = store.create_session(metadata={})

            store.append_event(sid, UserMessage(text="u1"))
            store.append_event(sid, AssistantMessage(text="a1"))
            store.append_event(sid, UserMessage(text="u2"))
            store.append_event(sid, AssistantMessage(text="a2"))

            events = store.read_events(sid)
            msgs = rebuild_messages(events, max_events=100, max_bytes=100_000)
            texts = [m.get("content") for m in msgs if m.get("role") in ("user", "assistant")]
            self.assertEqual(texts, ["u1", "a1", "u2", "a2"])

            # Revert to the first assistant message (seq=2).
            store.set_head(sid, head_seq=2, reason="test")
            events2 = store.read_events(sid)
            msgs2 = rebuild_messages(events2, max_events=100, max_bytes=100_000)
            texts2 = [m.get("content") for m in msgs2 if m.get("role") in ("user", "assistant")]
            self.assertEqual(texts2, ["u1", "a1"])

            # Undo should restore the prior head (full transcript).
            store.undo(sid)
            events3 = store.read_events(sid)
            msgs3 = rebuild_messages(events3, max_events=100, max_bytes=100_000)
            texts3 = [m.get("content") for m in msgs3 if m.get("role") in ("user", "assistant")]
            self.assertEqual(texts3, ["u1", "a1", "u2", "a2"])

            # Redo should re-apply the revert.
            store.redo(sid)
            events4 = store.read_events(sid)
            msgs4 = rebuild_messages(events4, max_events=100, max_bytes=100_000)
            texts4 = [m.get("content") for m in msgs4 if m.get("role") in ("user", "assistant")]
            self.assertEqual(texts4, ["u1", "a1"])


if __name__ == "__main__":
    unittest.main()
