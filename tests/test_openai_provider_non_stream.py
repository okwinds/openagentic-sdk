import unittest

from openagentic_sdk.providers.openai import OpenAIProvider


class TestOpenAIProvider(unittest.IsolatedAsyncioTestCase):
    async def test_complete_parses_tool_calls(self) -> None:
        seen = {}

        def transport(url, headers, payload):
            seen["url"] = url
            seen["headers"] = dict(headers)
            seen["payload"] = dict(payload)
            return {
                "id": "resp_1",
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_1",
                        "name": "Read",
                        "arguments": "{\"file_path\":\"a.txt\"}",
                    }
                ],
                "usage": {"total_tokens": 10},
            }

        p = OpenAIProvider(transport=transport)
        out = await p.complete(
            model="gpt-4.1-mini",
            input=[{"role": "user", "content": "read a.txt"}],
            tools=[],
            api_key="sk-test",
        )

        self.assertTrue(seen["url"].endswith("/responses"))
        self.assertIsNone(out.assistant_text)
        self.assertEqual(len(out.tool_calls), 1)
        self.assertEqual(out.tool_calls[0].name, "Read")
        self.assertEqual(out.tool_calls[0].arguments["file_path"], "a.txt")


if __name__ == "__main__":
    unittest.main()
