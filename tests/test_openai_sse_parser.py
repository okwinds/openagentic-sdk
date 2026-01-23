import unittest

from open_agent_sdk.providers.sse import parse_sse_events


class TestSSEParser(unittest.TestCase):
    def test_parses_data_lines(self) -> None:
        raw = b"data: {\\\"x\\\":1}\\n\\n" + b"data: [DONE]\\n\\n"
        events = list(parse_sse_events(raw.splitlines(keepends=True)))
        self.assertEqual(events[0], '{"x":1}')
        self.assertEqual(events[1], "[DONE]")


if __name__ == "__main__":
    unittest.main()

