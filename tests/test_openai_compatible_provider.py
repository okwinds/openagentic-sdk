import unittest

from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider


class TestOpenAICompatibleProvider(unittest.IsolatedAsyncioTestCase):
    async def test_uses_base_url_and_headers(self) -> None:
        seen = {}

        def transport(url, headers, payload):
            seen["url"] = url
            seen["headers"] = dict(headers)
            return {"id": "resp_1", "output": [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}]}

        p = OpenAICompatibleProvider(
            base_url="https://example.test/v1",
            transport=transport,
            api_key_header="x-api-key",
        )

        out = await p.complete(model="m", input=[{"role": "user", "content": "hi"}], api_key="k")
        self.assertIsInstance(out, ModelOutput)
        self.assertTrue(seen["url"].startswith("https://example.test/v1"))
        self.assertTrue(seen["url"].endswith("/responses"))
        self.assertEqual(seen["headers"]["x-api-key"], "k")

    async def test_stream_yields_text_and_tool_calls(self) -> None:
        chunks = [
            b'data: {"type":"response.created","response":{"id":"resp_1"}}\n\n',
            b'data: {"type":"response.output_item.added","output_index":0,"item":{"id":"msg_1","type":"message"}}\n\n',
            b'data: {"type":"response.output_text.delta","item_id":"msg_1","delta":"he"}\n\n',
            b'data: {"type":"response.output_text.delta","item_id":"msg_1","delta":"llo"}\n\n',
            b'data: {"type":"response.output_item.added","output_index":1,"item":{"id":"fc_1","type":"function_call","call_id":"call_1","name":"Read"}}\n\n',
            b'data: {"type":"response.function_call_arguments.delta","output_index":1,"delta":"{\\"file_path\\":\\"a.txt\\"}"}\n\n',
            b'data: {"type":"response.output_item.done","output_index":1,"item":{"id":"fc_1","type":"function_call","call_id":"call_1","name":"Read"}}\n\n',
            b'data: {"type":"response.completed","response":{"id":"resp_1"}}\n\n',
        ]

        def stream_transport(url, headers, payload):
            _ = (url, headers, payload)
            return iter(chunks)

        provider = OpenAICompatibleProvider(stream_transport=stream_transport)
        events = []
        async for ev in provider.stream(
            model="gpt-4.1-mini",
            input=[{"role": "user", "content": "read a.txt"}],
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
