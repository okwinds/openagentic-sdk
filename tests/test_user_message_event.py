import unittest

from openagentic_sdk.serialization import dumps_event, loads_event


class TestUserMessageEvent(unittest.TestCase):
    def test_roundtrip(self) -> None:
        from openagentic_sdk.events import UserMessage

        e1 = UserMessage(text="hi")
        raw = dumps_event(e1)
        e2 = loads_event(raw)
        self.assertEqual(e2, e1)


if __name__ == "__main__":
    unittest.main()

