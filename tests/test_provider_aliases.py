from __future__ import annotations

import json
import unittest

from openagentic_sdk.providers.aliases import GeminiProvider
from openagentic_sdk.providers.stream_events import DoneEvent, TextDeltaEvent, ToolCallEvent


class TestProviderAliases(unittest.IsolatedAsyncioTestCase):
    async def test_alias_complete_parses_text_and_tool_calls(self) -> None:
        def transport(url, headers, payload):  # noqa: ANN001
            _ = (url, headers, payload)
            return {
                "id": "r1",
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": "hello"}]},
                    {"type": "function_call", "call_id": "c1", "name": "Read", "arguments": "{}"},
                ],
                "usage": {"total_tokens": 3},
            }

        p = GeminiProvider(transport=transport, base_url="http://example")
        out = await p.complete(model="m", input=[{"role": "user", "content": "hi"}], api_key="k")
        self.assertEqual(out.assistant_text, "hello")
        self.assertEqual(len(out.tool_calls), 1)
        self.assertEqual(out.tool_calls[0].name, "Read")

    async def test_alias_stream_yields_deltas_tool_calls_and_done(self) -> None:
        def stream_transport(url, headers, payload):  # noqa: ANN001
            _ = (url, headers, payload)
            events = [
                {"type": "response.output_text.delta", "delta": "hi"},
                {"type": "response.output_item.added", "output_index": 0, "item": {"type": "function_call", "call_id": "c1", "name": "Grep"}},
                {"type": "response.function_call_arguments.delta", "output_index": 0, "delta": "{}"},
                {"type": "response.output_item.done", "output_index": 0, "item": {"type": "function_call", "call_id": "c1", "name": "Grep"}},
                {"type": "response.completed", "response": {"id": "r2", "usage": {"total_tokens": 5}}},
            ]
            out: list[bytes] = []
            for e in events:
                out.append(("data: " + json.dumps(e) + "\n").encode("utf-8"))
                out.append(b"\n")
            out.append(b"data: [DONE]\n")
            out.append(b"\n")
            return out

        p = GeminiProvider(stream_transport=stream_transport, base_url="http://example")
        seen_delta = False
        seen_tool = False
        seen_done = False
        async for ev in p.stream(model="m", input=[{"role": "user", "content": "hi"}], api_key="k"):
            if isinstance(ev, TextDeltaEvent):
                seen_delta = True
            if isinstance(ev, ToolCallEvent):
                seen_tool = True
                self.assertEqual(ev.tool_call.name, "Grep")
            if isinstance(ev, DoneEvent):
                seen_done = True
                self.assertEqual(ev.response_id, "r2")
        self.assertTrue(seen_delta)
        self.assertTrue(seen_tool)
        self.assertTrue(seen_done)


if __name__ == "__main__":
    unittest.main()
