import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestCliProviderAuthCommands(unittest.TestCase):
    def test_set_list_remove(self) -> None:
        from openagentic_cli.auth_cmd import cmd_auth_list, cmd_auth_remove, cmd_auth_set
        from openagentic_sdk.auth import all_auth

        with TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OPENAGENTIC_SDK_HOME"] = str(root / "oa-home")
            try:
                out = cmd_auth_set(provider_id="p1", key="secret")
                self.assertIn("p1", out)
                self.assertNotIn("secret", out)

                ids = cmd_auth_list().splitlines()
                self.assertIn("p1", ids)
                self.assertIn("p1", all_auth())

                out2 = cmd_auth_remove(provider_id="p1")
                self.assertIn("p1", out2)
                self.assertNotIn("p1", all_auth())
            finally:
                os.environ.pop("OPENAGENTIC_SDK_HOME", None)


if __name__ == "__main__":
    unittest.main()
