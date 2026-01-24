import unittest


class TestResponsesTypes(unittest.TestCase):
    def test_conversation_state_holds_previous_response_id(self) -> None:
        from openagentic_sdk.providers.responses_types import ResponsesConversationState

        st = ResponsesConversationState(previous_response_id="r1")
        self.assertEqual(st.previous_response_id, "r1")

    def test_model_output_carries_response_id(self) -> None:
        from openagentic_sdk.providers.base import ModelOutput

        out = ModelOutput(assistant_text="ok", tool_calls=[], response_id="r2")
        self.assertEqual(out.response_id, "r2")


if __name__ == "__main__":
    unittest.main()

