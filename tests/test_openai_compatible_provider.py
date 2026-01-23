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


if __name__ == "__main__":
    unittest.main()

