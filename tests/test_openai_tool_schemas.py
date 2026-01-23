import unittest

from open_agent_sdk.tools.openai import tool_schemas_for_openai


class TestOpenAiToolSchemas(unittest.TestCase):
    def test_websearch_array_items_present(self) -> None:
        schemas = tool_schemas_for_openai(["WebSearch"])
        self.assertEqual(len(schemas), 1)
        params = schemas[0]["function"]["parameters"]
        props = params["properties"]
        self.assertEqual(props["allowed_domains"]["type"], "array")
        self.assertEqual(props["allowed_domains"]["items"]["type"], "string")
        self.assertEqual(props["blocked_domains"]["type"], "array")
        self.assertEqual(props["blocked_domains"]["items"]["type"], "string")

    def test_ask_user_question_items_present(self) -> None:
        schemas = tool_schemas_for_openai(["AskUserQuestion"])
        params = schemas[0]["function"]["parameters"]
        props = params["properties"]
        self.assertEqual(props["questions"]["type"], "array")
        self.assertEqual(props["questions"]["items"]["type"], "object")


if __name__ == "__main__":
    unittest.main()

