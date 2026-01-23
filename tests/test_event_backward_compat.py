import unittest

from openagentic_sdk.serialization import loads_event


class TestEventBackwardCompat(unittest.TestCase):
    def test_unknown_fields_are_ignored(self) -> None:
        raw = '{"type":"assistant.message","text":"x","new_field":123}'
        e = loads_event(raw)
        self.assertEqual(getattr(e, "type", None), "assistant.message")
        self.assertEqual(getattr(e, "text", None), "x")


if __name__ == "__main__":
    unittest.main()

