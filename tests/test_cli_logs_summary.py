import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.events import Result, UserMessage
from openagentic_sdk.sessions.store import FileSessionStore


class TestCliLogsSummary(unittest.TestCase):
    def test_summarize_events_basic(self) -> None:
        from openagentic_cli.logs_cmd import summarize_events

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session(metadata={"cwd": str(root)})
            store.append_event(sid, UserMessage(text="hi"))
            store.append_event(
                sid,
                Result(
                    final_text="ok",
                    session_id=sid,
                    stop_reason="end",
                    response_id="resp_1",
                    provider_metadata={"protocol": "responses"},
                ),
            )

            events = store.read_events(sid)
            out = summarize_events(events)
            self.assertIn("user.message", out)
            self.assertIn("Protocol: responses", out)


if __name__ == "__main__":
    unittest.main()
