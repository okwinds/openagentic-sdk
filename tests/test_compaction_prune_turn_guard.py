import unittest


class TestCompactionPruneTurnGuard(unittest.TestCase):
    def test_does_not_prune_until_two_user_turns(self) -> None:
        from openagentic_sdk.compaction import CompactionOptions, select_tool_outputs_to_prune
        from openagentic_sdk.events import ToolResult, UserMessage

        events = [
            UserMessage(text="u1"),
            ToolResult(tool_use_id="t1", output={"big": "x" * 10000}),
        ]

        ids = select_tool_outputs_to_prune(events=events, compaction=CompactionOptions(prune=True, protect_tool_output_tokens=1, min_prune_tokens=1))
        self.assertEqual(ids, [])


if __name__ == "__main__":
    unittest.main()
