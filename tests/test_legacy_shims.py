import unittest
import warnings
import importlib


class TestLegacyShims(unittest.TestCase):
    def test_open_agent_sdk_alias(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            m = importlib.import_module("open_agent_sdk")
            importlib.reload(m)

        self.assertTrue(any(issubclass(x.category, DeprecationWarning) for x in w))
        self.assertTrue(hasattr(m, "query"))

    def test_open_agent_cli_alias(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            m = importlib.import_module("open_agent_cli")
            importlib.reload(m)

        self.assertTrue(any(issubclass(x.category, DeprecationWarning) for x in w))
        self.assertTrue(hasattr(m, "__file__"))


if __name__ == "__main__":
    unittest.main()
