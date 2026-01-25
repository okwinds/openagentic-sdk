import unittest


class TestCompactionPruneProtectedTools(unittest.TestCase):
    def test_skill_tool_results_are_never_pruned(self) -> None:
        from openagentic_sdk.compaction import CompactionOptions, select_tool_outputs_to_prune
        from openagentic_sdk.events import ToolResult, ToolUse, UserMessage

        # Two user turns present.
        events = [
            UserMessage(text="u1"),
            ToolUse(tool_use_id="s1", name="Skill", input={"name": "x"}),
            ToolResult(tool_use_id="s1", output={"content": "x" * 10000}),
            UserMessage(text="u2"),
        ]

        ids = select_tool_outputs_to_prune(
            events=events,
            compaction=CompactionOptions(prune=True, protect_tool_output_tokens=1, min_prune_tokens=1),
        )
        self.assertNotIn("s1", ids)


if __name__ == "__main__":
    unittest.main()
