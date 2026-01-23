import unittest

from openagentic_sdk.providers.openai import OpenAIProvider


class TestOpenAIProvider(unittest.IsolatedAsyncioTestCase):
    async def test_complete_parses_tool_calls(self) -> None:
        def transport(url, headers, payload):
            return {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "Read", "arguments": "{\"file_path\":\"a.txt\"}"},
                                }
                            ],
                        }
                    }
                ],
                "usage": {"total_tokens": 10},
            }

        p = OpenAIProvider(transport=transport)
        out = await p.complete(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": "read a.txt"}],
            tools=[],
            api_key="sk-test",
        )
        self.assertIsNone(out.assistant_text)
        self.assertEqual(len(out.tool_calls), 1)
        self.assertEqual(out.tool_calls[0].name, "Read")
        self.assertEqual(out.tool_calls[0].arguments["file_path"], "a.txt")


if __name__ == "__main__":
    unittest.main()

