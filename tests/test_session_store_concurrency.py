import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


class TestFileSessionStoreConcurrency(unittest.TestCase):
    def test_append_event_is_serialized_per_session(self) -> None:
        from openagentic_sdk.events import UserMessage
        from openagentic_sdk.sessions.store import FileSessionStore
        import openagentic_sdk.sessions.store as store_mod

        entered = threading.Event()
        release = threading.Event()
        overlap = threading.Event()
        in_critical_section = threading.Event()

        real_event_to_dict = store_mod.event_to_dict

        def guarded_event_to_dict(event):  # noqa: ANN001
            if in_critical_section.is_set():
                overlap.set()
            in_critical_section.set()
            entered.set()
            try:
                release.wait(timeout=1.0)
                return real_event_to_dict(event)
            finally:
                in_critical_section.clear()

        with TemporaryDirectory() as td:
            store = FileSessionStore(root_dir=Path(td))
            sid = store.create_session(metadata={"title": "t"})

            def worker() -> None:
                store.append_event(sid, UserMessage(text="hi"))

            with mock.patch.object(store_mod, "event_to_dict", side_effect=guarded_event_to_dict):
                t1 = threading.Thread(target=worker)
                t2 = threading.Thread(target=worker)
                t1.start()
                self.assertTrue(entered.wait(timeout=1.0))
                t2.start()
                release.set()
                t1.join(timeout=2.0)
                t2.join(timeout=2.0)

        self.assertFalse(overlap.is_set(), "append_event executed concurrently for the same session")

