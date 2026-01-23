import json
import unittest


class TestCliRunJson(unittest.TestCase):
    def test_json_shape(self) -> None:
        from openagentic_cli.run_cmd import format_run_json

        s = format_run_json(final_text="ok", session_id="sid", stop_reason="end")
        obj = json.loads(s)
        self.assertEqual(obj["final_text"], "ok")
        self.assertEqual(obj["session_id"], "sid")


if __name__ == "__main__":
    unittest.main()

