from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.events import AssistantMessage, UserMessage
from openagentic_sdk.sessions.store import FileSessionStore


class TestSessionFork(unittest.TestCase):
    def test_fork_session_copies_events_and_writes_parent_metadata(self) -> None:
        with TemporaryDirectory() as td:
            store = FileSessionStore(root_dir=Path(td))
            parent = store.create_session(metadata={"x": 1})

            store.append_event(parent, UserMessage(text="u1"))
            store.append_event(parent, AssistantMessage(text="a1"))
            store.append_event(parent, UserMessage(text="u2"))

            child = store.fork_session(parent, head_seq=2)
            child_events = store.read_events(child)
            child_texts = [(e.type, getattr(e, "text", "")) for e in child_events]
            self.assertEqual(child_texts, [("user.message", "u1"), ("assistant.message", "a1")])

            md = store.read_metadata(child)
            self.assertEqual(md.get("parent_session_id"), parent)
            self.assertEqual(md.get("parent_head_seq"), 2)


if __name__ == "__main__":
    unittest.main()
