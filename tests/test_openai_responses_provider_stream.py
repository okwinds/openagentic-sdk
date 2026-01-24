import unittest


def _sse(*payloads: str) -> list[bytes]:
    out: list[bytes] = []
    for p in payloads:
        out.append(f"data: {p}\n\n".encode("utf-8"))
    return out


class TestOpenAIResponsesProviderStream(unittest.IsolatedAsyncioTestCase):
    async def test_stream_yields_text_and_tool_calls(self) -> None:
        chunks = _sse(
            '{"type":"response.created","response":{"id":"resp_1"}}',
            '{"type":"response.output_item.added","output_index":0,"item":{"id":"msg_1","type":"message"}}',
            '{"type":"response.output_text.delta","item_id":"msg_1","delta":"he"}',
            '{"type":"response.output_text.delta","item_id":"msg_1","delta":"llo"}',
            '{"type":"response.output_item.added","output_index":1,"item":{"id":"fc_1","type":"function_call","call_id":"call_1","name":"Read"}}',
            '{"type":"response.function_call_arguments.delta","output_index":1,"delta":"{\\"file_path\\":\\"a.txt\\"}"}',
            '{"type":"response.output_item.done","output_index":1,"item":{"id":"fc_1","type":"function_call","call_id":"call_1","name":"Read"}}',
            '{"type":"response.completed","response":{"id":"resp_1","usage":{"total_tokens":10}}}',
        )

        def stream_transport(url, headers, payload):
            _ = (url, headers, payload)
            return iter(chunks)

        from openagentic_sdk.providers.openai_responses import OpenAIResponsesProvider

        provider = OpenAIResponsesProvider(stream_transport=stream_transport)
        events = []
        async for ev in provider.stream(
            model="m",
            input=[{"role": "user", "content": "read a.txt"}],
            tools=[],
            api_key="k",
        ):
            events.append(ev)

        text = "".join(getattr(e, "delta", "") for e in events if getattr(e, "type", None) == "text_delta")
        self.assertEqual(text, "hello")

        tool_calls = [getattr(e, "tool_call", None) for e in events if getattr(e, "type", None) == "tool_call"]
        tool_calls = [tc for tc in tool_calls if tc is not None]
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].tool_use_id, "call_1")
        self.assertEqual(tool_calls[0].name, "Read")
        self.assertEqual(tool_calls[0].arguments["file_path"], "a.txt")

        self.assertTrue(any(getattr(e, "type", None) == "done" for e in events))


if __name__ == "__main__":
    unittest.main()

