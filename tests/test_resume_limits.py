import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.events import AssistantMessage, SystemInit
from open_agent_sdk.sessions.rebuild import rebuild_messages
from open_agent_sdk.sessions.store import FileSessionStore


class TestResumeLimits(unittest.TestCase):
    def test_rebuild_applies_max_events(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session()
            store.append_event(sid, SystemInit(session_id=sid, cwd="/x", sdk_version="0.0.0"))
            for i in range(2000):
                store.append_event(sid, AssistantMessage(text=f"m{i}"))

            events = store.read_events(sid)
            msgs = rebuild_messages(events, max_events=200, max_bytes=10_000_000)
            self.assertLessEqual(len(msgs), 200)

    def test_rebuild_applies_max_bytes(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session()
            store.append_event(sid, SystemInit(session_id=sid, cwd="/x", sdk_version="0.0.0"))
            for _i in range(200):
                store.append_event(sid, AssistantMessage(text="x" * 1000))

            events = store.read_events(sid)
            msgs = rebuild_messages(events, max_events=1000, max_bytes=10_000)
            total = sum(len((m.get("content") or "").encode("utf-8")) for m in msgs)
            self.assertLessEqual(total, 10_000)


if __name__ == "__main__":
    unittest.main()

