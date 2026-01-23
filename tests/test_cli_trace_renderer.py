import io
import unittest

from open_agent_sdk.events import AssistantDelta, AssistantMessage, HookEvent, ToolResult, ToolUse


class TestCliTraceRenderer(unittest.TestCase):
    def test_groups_tools_and_summarizes(self) -> None:
        from open_agent_cli.trace import TraceRenderer

        out = io.StringIO()
        r = TraceRenderer(stream=out, color=False)

        r.on_event(ToolUse(tool_use_id="t1", name="Grep", input={"query": "x", "file_glob": "**/*.py"}))
        r.on_event(ToolResult(tool_use_id="t1", output={"total_matches": 2}, is_error=False))

        r.on_event(ToolUse(tool_use_id="t2", name="Bash", input={"command": "pwd"}))
        r.on_event(ToolResult(tool_use_id="t2", output={"exit_code": 0, "output": "/x\n"}, is_error=False))

        s = out.getvalue()
        self.assertIn("• Explored", s)
        self.assertIn("Search", s)
        self.assertIn("• Ran", s)
        self.assertIn("pwd", s)
        self.assertIn("exit_code=0", s)

    def test_rg_help_is_printed_when_missing_pattern(self) -> None:
        from open_agent_cli.trace import TraceRenderer

        out = io.StringIO()
        r = TraceRenderer(stream=out, color=False)
        r.on_event(ToolUse(tool_use_id="t1", name="Bash", input={"command": "rg"}))
        r.on_event(
            ToolResult(
                tool_use_id="t1",
                output={"exit_code": 2, "output": "rg: ripgrep requires at least one pattern to execute a search\n"},
                is_error=False,
            )
        )
        self.assertIn("hint:", out.getvalue())

    def test_rg_help_is_printed_when_rg_missing(self) -> None:
        from open_agent_cli.trace import TraceRenderer

        out = io.StringIO()
        r = TraceRenderer(stream=out, color=False)
        r.on_event(ToolUse(tool_use_id="t1", name="Bash", input={"command": "rg foo"}))
        r.on_event(
            ToolResult(
                tool_use_id="t1",
                output={"exit_code": 127, "output": "bash: rg: command not found\n"},
                is_error=False,
            )
        )
        s = out.getvalue()
        self.assertIn("winget install BurntSushi.ripgrep.MSVC", s)

    def test_streaming_deltas_do_not_duplicate_final(self) -> None:
        from open_agent_cli.trace import TraceRenderer

        out = io.StringIO()
        r = TraceRenderer(stream=out, color=False)
        r.on_event(AssistantDelta(text_delta="hi"))
        r.on_event(AssistantMessage(text="hi"))
        self.assertEqual(out.getvalue(), "hi\n")

    def test_hook_event_is_rendered(self) -> None:
        from open_agent_cli.trace import TraceRenderer

        out = io.StringIO()
        r = TraceRenderer(stream=out, color=False, show_hooks=True)
        r.on_event(HookEvent(hook_point="BeforeModelCall", name="x", matched=True, action="rewrite_messages"))
        self.assertIn("• Hooks", out.getvalue())

    def test_error_message_is_rendered(self) -> None:
        from open_agent_cli.trace import TraceRenderer

        out = io.StringIO()
        r = TraceRenderer(stream=out, color=False)
        r.on_event(ToolUse(tool_use_id="t1", name="Read", input={"file_path": "x"}))
        r.on_event(ToolResult(tool_use_id="t1", output=None, is_error=True, error_message="boom"))
        self.assertIn("ERROR: boom", out.getvalue())


if __name__ == "__main__":
    unittest.main()
