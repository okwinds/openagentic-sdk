import io
import json
import unittest


class TestConsoleRenderer(unittest.TestCase):
    def test_renderer_dedupes_streaming(self) -> None:
        from open_agent_sdk.console import ConsoleRenderer
        from open_agent_sdk.events import AssistantDelta, AssistantMessage

        buf = io.StringIO()
        r = ConsoleRenderer(stream=buf, debug=False)
        r.on_event(AssistantDelta(text_delta="hello "))
        r.on_event(AssistantDelta(text_delta="world"))
        r.on_event(AssistantMessage(text="hello world"))
        self.assertEqual(buf.getvalue(), "hello world\n")

    def test_renderer_prints_todowrite_list_from_events(self) -> None:
        from open_agent_sdk.console import ConsoleRenderer
        from open_agent_sdk.events import ToolResult, ToolUse

        buf = io.StringIO()
        r = ConsoleRenderer(stream=buf, debug=False)

        r.on_event(
            ToolUse(
                tool_use_id="t1",
                name="TodoWrite",
                input={
                    "todos": [
                        {"content": "A", "activeForm": "Doing A", "status": "in_progress"},
                        {"content": "B", "activeForm": "Do B", "status": "pending"},
                    ]
                },
            )
        )
        r.on_event(
            ToolResult(
                tool_use_id="t1",
                output={"message": "Updated todos", "stats": {"total": 2, "pending": 1, "in_progress": 1, "completed": 0}},
                is_error=False,
            )
        )
        out = buf.getvalue()
        self.assertIn("TODOs:", out)
        self.assertIn("- [in_progress] Doing A", out)
        self.assertIn("- [pending] Do B", out)

    def test_renderer_prints_todowrite_list_from_messages(self) -> None:
        from open_agent_sdk.console import ConsoleRenderer
        from open_agent_sdk.messages import AssistantMessage, ToolResultBlock, ToolUseBlock

        buf = io.StringIO()
        r = ConsoleRenderer(stream=buf, debug=False)

        r.on_message(
            AssistantMessage(
                model="m",
                content=[
                    ToolUseBlock(
                        id="t1",
                        name="TodoWrite",
                        input={
                            "todos": [
                                {"content": "A", "activeForm": "Doing A", "status": "in_progress"},
                            ]
                        },
                    )
                ],
            )
        )
        r.on_message(
            AssistantMessage(
                model="m",
                content=[
                    ToolResultBlock(
                        tool_use_id="t1",
                        content=json.dumps(
                            {"message": "Updated todos", "stats": {"total": 1, "pending": 0, "in_progress": 1, "completed": 0}}
                        ),
                        is_error=False,
                    )
                ],
            )
        )
        out = buf.getvalue()
        self.assertIn("- [in_progress] Doing A", out)

    def test_renderer_dedupes_streaming_messages(self) -> None:
        from open_agent_sdk.console import ConsoleRenderer
        from open_agent_sdk.messages import AssistantMessage, StreamEvent, TextBlock

        buf = io.StringIO()
        r = ConsoleRenderer(stream=buf, debug=False)
        r.on_message(StreamEvent(uuid="u", session_id="s", event={"type": "text_delta", "delta": "hello "}))
        r.on_message(StreamEvent(uuid="u2", session_id="s", event={"type": "text_delta", "delta": "world"}))
        r.on_message(AssistantMessage(model="m", content=[TextBlock(text="hello world")]))
        self.assertEqual(buf.getvalue(), "hello world\n")

    def test_renderer_hides_result_message_by_default(self) -> None:
        from open_agent_sdk.console import ConsoleRenderer
        from open_agent_sdk.messages import ResultMessage

        buf = io.StringIO()
        r = ConsoleRenderer(stream=buf, debug=False)
        r.on_message(
            ResultMessage(
                subtype="success",
                duration_ms=1,
                duration_api_ms=0,
                is_error=False,
                num_turns=1,
                session_id="s",
                result="ok",
            )
        )
        self.assertEqual(buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
