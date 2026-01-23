import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.events import SystemInit
from openagentic_sdk.sessions.store import FileSessionStore


class TestEventSeqTs(unittest.TestCase):
    def test_events_have_seq_and_ts_in_jsonl(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session()

            store.append_event(sid, SystemInit(session_id=sid, cwd="/x", sdk_version="0.0.0"))
            store.append_event(sid, SystemInit(session_id=sid, cwd="/y", sdk_version="0.0.0"))

            p = root / "sessions" / sid / "events.jsonl"
            lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2)
            o1 = json.loads(lines[0])
            o2 = json.loads(lines[1])

            self.assertIsInstance(o1.get("seq"), int)
            self.assertIsInstance(o2.get("seq"), int)
            self.assertEqual(o1["seq"], 1)
            self.assertEqual(o2["seq"], 2)

            self.assertIsInstance(o1.get("ts"), (int, float))
            self.assertIsInstance(o2.get("ts"), (int, float))
            self.assertLessEqual(o1["ts"], o2["ts"])


if __name__ == "__main__":
    unittest.main()

