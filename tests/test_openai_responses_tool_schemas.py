import unittest
from pathlib import Path


class TestOpenAIResponsesToolSchemas(unittest.TestCase):
    def test_function_shape_is_responses_style(self) -> None:
        from openagentic_sdk.tools.openai_responses import tool_schemas_for_responses

        schemas = tool_schemas_for_responses(["Read"])
        self.assertEqual(len(schemas), 1)
        tool = schemas[0]
        self.assertEqual(tool.get("type"), "function")
        self.assertEqual(tool.get("name"), "Read")
        self.assertTrue(isinstance(tool.get("parameters"), dict))
        self.assertFalse("function" in tool)

    def test_skill_schema_description_is_preserved(self) -> None:
        from openagentic_sdk.tools.openai_responses import tool_schemas_for_responses

        project_dir = Path(__file__).resolve().parents[1] / "example"
        schemas = tool_schemas_for_responses(["Skill"], context={"project_dir": str(project_dir)})
        desc = schemas[0]["description"]
        self.assertIn("Only the skills listed here are available", desc)
        self.assertIn("main-process", desc)
        self.assertIn("drawing", desc)


if __name__ == "__main__":
    unittest.main()

