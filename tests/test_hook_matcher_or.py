import unittest

from open_agent_sdk.hooks.engine import _match_name


class TestHookMatcherOr(unittest.TestCase):
    def test_or(self) -> None:
        self.assertTrue(_match_name("Edit|Write", "Edit"))
        self.assertTrue(_match_name("Edit|Write", "Write"))
        self.assertFalse(_match_name("Edit|Write", "Read"))


if __name__ == "__main__":
    unittest.main()

