import unittest

from open_agent_sdk.providers.base import ModelOutput
from open_agent_sdk.providers.openai_compatible import OpenAICompatibleProvider


class TestOpenAICompatibleProvider(unittest.IsolatedAsyncioTestCase):
    async def test_uses_base_url_and_headers(self) -> None:
        seen = {}

        def transport(url, headers, payload):
            seen["url"] = url
            seen["headers"] = dict(headers)
            return {"choices": [{"message": {"content": "ok"}}]}

        p = OpenAICompatibleProvider(
            base_url="https://example.test/v1",
            transport=transport,
            api_key_header="x-api-key",
        )

        out = await p.complete(model="m", messages=[{"role": "user", "content": "hi"}], api_key="k")
        self.assertIsInstance(out, ModelOutput)
        self.assertTrue(seen["url"].startswith("https://example.test/v1"))
        self.assertEqual(seen["headers"]["x-api-key"], "k")

    async def test_stream_yields_text_and_tool_calls(self) -> None:
        chunks = [
            b'data: {"choices":[{"delta":{"content":"he"}}]}\n\n',
            b'data: {"choices":[{"delta":{"content":"llo"}}]}\n\n',
            b'data: {"choices":[{"delta":{"tool_calls":[{"id":"call_1","function":{"name":"Read","arguments":"{\\"file_"}}]}}]}\n\n',
            b'data: {"choices":[{"delta":{"tool_calls":[{"id":"call_1","function":{"arguments":"path\\":\\"a.txt\\"}"}}]}}]}\n\n',
            b"data: [DONE]\n\n",
        ]

        def stream_transport(url, headers, payload):
            _ = (url, headers, payload)
            return iter(chunks)

        provider = OpenAICompatibleProvider(stream_transport=stream_transport)
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
