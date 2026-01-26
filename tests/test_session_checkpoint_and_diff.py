from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.events import AssistantMessage, SessionCheckpoint, UserMessage
from openagentic_sdk.sessions.diff import transcript_from_messages, unified_diff
from openagentic_sdk.sessions.rebuild import rebuild_messages
from openagentic_sdk.sessions.store import FileSessionStore


class TestSessionCheckpointAndDiff(unittest.TestCase):
    def test_checkpoint_captures_head_seq(self) -> None:
        with TemporaryDirectory() as td:
            store = FileSessionStore(root_dir=Path(td))
            sid = store.create_session(metadata={})

            store.append_event(sid, UserMessage(text="u1"))
            store.append_event(sid, AssistantMessage(text="a1"))
            store.checkpoint(sid, label="cp1")

            events = store.read_events(sid)
            last = events[-1]
            self.assertIsInstance(last, SessionCheckpoint)
            self.assertEqual(getattr(last, "head_seq"), 2)

    def test_diff_helpers(self) -> None:
        a = transcript_from_messages([
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "ok"},
        ])
        b = transcript_from_messages([
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "changed"},
        ])
        d = unified_diff(a, b, fromfile="a", tofile="b")
        self.assertIn("-ok", d)
        self.assertIn("+changed", d)


if __name__ == "__main__":
    unittest.main()
