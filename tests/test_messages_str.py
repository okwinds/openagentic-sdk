import unittest


class TestMessagesStr(unittest.TestCase):
    def test_assistant_text_str(self) -> None:
        from open_agent_sdk.messages import AssistantMessage, TextBlock

        m = AssistantMessage(model="m", content=[TextBlock(text="Hello")])
        self.assertEqual(str(m), "Hello")

    def test_tool_use_str_is_compact(self) -> None:
        from open_agent_sdk.messages import AssistantMessage, ToolUseBlock

        m = AssistantMessage(model="m", content=[ToolUseBlock(id="t1", name="Read", input={"file_path": "a.txt"})])
        s = str(m)
        self.assertIn("[tool.use] Read", s)
        self.assertIn("id=t1", s)
        self.assertIn("file_path", s)

    def test_tool_result_str_is_compact(self) -> None:
        from open_agent_sdk.messages import AssistantMessage, ToolResultBlock

        m = AssistantMessage(model="m", content=[ToolResultBlock(tool_use_id="t1", content='{"ok":true}', is_error=False)])
        s = str(m)
        self.assertIn("[tool.result] t1 ok", s)

    def test_result_message_does_not_duplicate_text(self) -> None:
        from open_agent_sdk.messages import ResultMessage

        m = ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=0,
            is_error=False,
            num_turns=1,
            session_id="s",
            result="FINAL_TEXT",
        )
        self.assertEqual(str(m), "[done] session_id=s")
        self.assertNotIn("FINAL_TEXT", str(m))


if __name__ == "__main__":
    unittest.main()

