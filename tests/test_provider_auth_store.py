import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestProviderAuthStore(unittest.TestCase):
    def test_roundtrip_and_permissions(self) -> None:
        from openagentic_sdk.auth import ApiAuth, all_auth, remove_auth, set_auth

        with TemporaryDirectory() as td:
            os.environ["OPENAGENTIC_SDK_HOME"] = td
            try:
                set_auth("p1", ApiAuth(key="k1"))
                data = all_auth()
                self.assertIn("p1", data)
                self.assertEqual(getattr(data["p1"], "type", None), "api")

                # Remove and confirm deletion.
                remove_auth("p1")
                data2 = all_auth()
                self.assertNotIn("p1", data2)

                # Best-effort file permission hardening (skip on Windows).
                p = Path(td) / "auth.json"
                if os.name != "nt" and p.exists():
                    mode = int(p.stat().st_mode) & 0o777
                    # No group/other permissions.
                    self.assertEqual(mode & 0o077, 0)
            finally:
                os.environ.pop("OPENAGENTIC_SDK_HOME", None)


if __name__ == "__main__":
    unittest.main()
