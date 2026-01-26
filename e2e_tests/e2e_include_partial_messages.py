from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk import AssistantMessage, ResultMessage, StreamEvent, query_messages

from e2e_tests._harness import make_options


class TestE2EIncludePartialMessages(unittest.IsolatedAsyncioTestCase):
    async def test_includes_stream_events_when_enabled(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            opts0 = make_options(root, allowed_tools=[])
            opts = replace(opts0, include_partial_messages=True)

            saw_delta = False
            saw_final = False
            saw_result = False

            async for msg in query_messages(prompt="Write a short 2-sentence answer about recursion.", options=opts):
                if isinstance(msg, StreamEvent) and msg.event.get("type") == "text_delta":
                    saw_delta = True
                if isinstance(msg, AssistantMessage):
                    saw_final = True
                if isinstance(msg, ResultMessage):
                    saw_result = True

            self.assertTrue(saw_delta)
            self.assertTrue(saw_final)
            self.assertTrue(saw_result)


if __name__ == "__main__":
    unittest.main()

