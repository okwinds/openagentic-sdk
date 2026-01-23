import unittest

from openagentic_sdk.providers.openai_stream_assembler import ToolCallAssembler


class TestToolCallAssembler(unittest.TestCase):
    def test_assembles_arguments(self) -> None:
        a = ToolCallAssembler()
        a.apply_delta({"id": "call_1", "function": {"name": "Read", "arguments": "{\"file_"}})
        a.apply_delta({"id": "call_1", "function": {"arguments": "path\":\"a.txt\"}"}})
        calls = a.finalize()
        self.assertEqual(calls[0].name, "Read")
        self.assertEqual(calls[0].arguments["file_path"], "a.txt")


if __name__ == "__main__":
    unittest.main()

