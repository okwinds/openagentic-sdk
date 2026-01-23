import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.events import UserMessage
from open_agent_sdk.sessions.store import FileSessionStore


class TestCliLogsSummary(unittest.TestCase):
    def test_summarize_events_basic(self) -> None:
        from open_agent_cli.logs_cmd import summarize_events

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session(metadata={"cwd": str(root)})
            store.append_event(sid, UserMessage(text="hi"))

            events = store.read_events(sid)
            out = summarize_events(events)
            self.assertIn("user.message", out)


if __name__ == "__main__":
    unittest.main()

