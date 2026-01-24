import unittest

from openagentic_sdk.events import Result, SystemInit
from openagentic_sdk.serialization import dumps_event, loads_event


class TestEventRoundtrip(unittest.TestCase):
    def test_event_roundtrip_system_init(self) -> None:
        e1 = SystemInit(session_id="s1", cwd="/tmp", sdk_version="0.0.0")
        raw = dumps_event(e1)
        e2 = loads_event(raw)
        self.assertEqual(e2, e1)

    def test_event_roundtrip_result_with_response_id(self) -> None:
        e1 = Result(
            session_id="s1",
            final_text="ok",
            stop_reason="end",
            steps=1,
            usage={"total_tokens": 10},
            response_id="resp_1",
            provider_metadata={"service_tier": "auto"},
        )
        raw = dumps_event(e1)
        e2 = loads_event(raw)
        self.assertEqual(e2, e1)


if __name__ == "__main__":
    unittest.main()
