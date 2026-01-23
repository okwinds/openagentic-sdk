import unittest

from openagentic_sdk.events import SystemInit
from openagentic_sdk.serialization import dumps_event, loads_event


class TestEventRoundtrip(unittest.TestCase):
    def test_event_roundtrip_system_init(self) -> None:
        e1 = SystemInit(session_id="s1", cwd="/tmp", sdk_version="0.0.0")
        raw = dumps_event(e1)
        e2 = loads_event(raw)
        self.assertEqual(e2, e1)


if __name__ == "__main__":
    unittest.main()

