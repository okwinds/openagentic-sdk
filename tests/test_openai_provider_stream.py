import unittest

from openagentic_sdk.providers.openai import OpenAIProvider


def _sse(*payloads: str) -> list[bytes]:
    out: list[bytes] = []
    for p in payloads:
        out.append(f"data: {p}\n\n".encode("utf-8"))
    return out


class TestOpenAIProviderStream(unittest.IsolatedAsyncioTestCase):
    async def test_stream_yields_text_and_tool_calls(self) -> None:
        chunks = _sse(
            '{"choices":[{"delta":{"content":"he"}}]}',
            '{"choices":[{"delta":{"content":"llo"}}]}',
            '{"choices":[{"delta":{"tool_calls":[{"id":"call_1","function":{"name":"Read","arguments":"{\\"file_"}}]}}]}',
            '{"choices":[{"delta":{"tool_calls":[{"id":"call_1","function":{"arguments":"path\\":\\"a.txt\\"}"}}]}}]}',
            "[DONE]",
        )

        def stream_transport(url, headers, payload):
            _ = (url, headers, payload)
            return iter(chunks)

        provider = OpenAIProvider(stream_transport=stream_transport)
        events = []
        async for ev in provider.stream(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": "read a.txt"}],
            tools=[],
            api_key="sk-test",
        ):
            events.append(ev)

        text = "".join(e.delta for e in events if e.type == "text_delta")
        self.assertEqual(text, "hello")

        tool_calls = [e.tool_call for e in events if e.type == "tool_call"]
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].name, "Read")
        self.assertEqual(tool_calls[0].arguments["file_path"], "a.txt")


if __name__ == "__main__":
    unittest.main()

