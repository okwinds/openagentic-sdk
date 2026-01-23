import unittest

from open_agent_sdk.messages import AssistantMessage, TextBlock, ToolUseBlock


class TestBlocks(unittest.TestCase):
    def test_blocks_construct(self) -> None:
        self.assertEqual(TextBlock(text="x").text, "x")
        b = ToolUseBlock(id="t1", name="Read", input={"file_path": "a"})
        self.assertEqual(b.name, "Read")
        msg = AssistantMessage(content=[b], model="m")
        self.assertEqual(msg.model, "m")


if __name__ == "__main__":
    unittest.main()

