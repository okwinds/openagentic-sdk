import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.events import SystemInit
from open_agent_sdk.sessions.store import FileSessionStore


class TestSessionStore(unittest.TestCase):
    def test_session_store_writes_events(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session()
            store.append_event(sid, SystemInit(session_id=sid, cwd="/x", sdk_version="0.0.0"))

            p = root / "sessions" / sid / "events.jsonl"
            self.assertTrue(p.exists())
            self.assertNotEqual(p.read_text(encoding="utf-8").strip(), "")

            events = store.read_events(sid)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].type, "system.init")


if __name__ == "__main__":
    unittest.main()

