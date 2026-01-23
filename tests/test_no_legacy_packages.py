import importlib
import unittest


class TestNoLegacyPackages(unittest.TestCase):
    def test_open_agent_sdk_missing(self) -> None:
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("open_agent_sdk")

    def test_open_agent_cli_missing(self) -> None:
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("open_agent_cli")


if __name__ == "__main__":
    unittest.main()

