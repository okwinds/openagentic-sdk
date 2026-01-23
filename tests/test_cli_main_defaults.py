import os
import unittest


class TestCliMainDefaults(unittest.TestCase):
    def test_default_permission_mode_is_default(self) -> None:
        import open_agent_cli.__main__ as m

        os.environ.pop("OA_PERMISSION_MODE", None)
        self.assertEqual(m.default_permission_mode(), "default")


if __name__ == "__main__":
    unittest.main()

