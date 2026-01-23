import unittest

from openagentic_sdk.serialization import loads_event


class TestUnknownEventType(unittest.TestCase):
    def test_unknown_type(self) -> None:
        from openagentic_sdk.errors import UnknownEventTypeError

        with self.assertRaises(UnknownEventTypeError):
            loads_event('{"type":"nope"}')


if __name__ == "__main__":
    unittest.main()

