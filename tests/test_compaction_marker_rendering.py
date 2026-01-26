import unittest


class TestCompactionMarkerRendering(unittest.TestCase):
    def test_rebuild_renders_compaction_marker_as_user_text(self) -> None:
        from openagentic_sdk.compaction import COMPACTION_MARKER_QUESTION
        from openagentic_sdk.events import AssistantMessage, UserCompaction
        from openagentic_sdk.sessions.rebuild import rebuild_messages

        events = [
            AssistantMessage(text="hi"),
            UserCompaction(auto=True, reason="overflow"),
        ]
        msgs = rebuild_messages(events, max_events=100, max_bytes=1_000_000)
        user_texts = [m.get("content") for m in msgs if m.get("role") == "user"]
        self.assertIn(COMPACTION_MARKER_QUESTION, user_texts)


if __name__ == "__main__":
    unittest.main()
