import unittest


class TestOpenAIResponsesProviderNonStream(unittest.IsolatedAsyncioTestCase):
    async def test_complete_posts_to_responses_and_parses_output(self) -> None:
        seen = {}

        def transport(url, headers, payload):
            seen["url"] = url
            seen["headers"] = dict(headers)
            seen["payload"] = dict(payload)
            return {
                "id": "resp_1",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "hello"}],
                    },
                    {
                        "type": "function_call",
                        "call_id": "call_1",
                        "name": "Read",
                        "arguments": '{"file_path":"a.txt"}',
                    },
                ],
                "usage": {"total_tokens": 10},
            }

        from openagentic_sdk.providers.openai_responses import OpenAIResponsesProvider

        p = OpenAIResponsesProvider(base_url="https://example.test/v1", api_key_header="x-api-key", transport=transport)
        out = await p.complete(
            model="m",
            input=[{"role": "user", "content": "read a.txt"}],
            tools=[{"type": "function", "name": "Read", "parameters": {"type": "object", "properties": {}}}],
            api_key="k",
            previous_response_id="resp_0",
        )

        self.assertEqual(seen["url"], "https://example.test/v1/responses")
        self.assertEqual(seen["headers"]["x-api-key"], "k")
        self.assertEqual(seen["payload"]["model"], "m")
        self.assertEqual(seen["payload"]["previous_response_id"], "resp_0")
        self.assertTrue(seen["payload"]["store"])

        self.assertEqual(out.assistant_text, "hello")
        self.assertEqual(out.response_id, "resp_1")
        self.assertEqual(len(out.tool_calls), 1)
        self.assertEqual(out.tool_calls[0].tool_use_id, "call_1")
        self.assertEqual(out.tool_calls[0].name, "Read")
        self.assertEqual(out.tool_calls[0].arguments["file_path"], "a.txt")


if __name__ == "__main__":
    unittest.main()

