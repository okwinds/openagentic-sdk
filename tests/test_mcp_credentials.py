from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from openagentic_sdk.mcp.credentials import McpCredentialStore


class TestMcpCredentialStore(unittest.TestCase):
    def test_store_and_merge_headers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ["OPENAGENTIC_SDK_HOME"] = td

            store = McpCredentialStore.load_default()
            store.set_bearer_token("srv", "t1")
            store.save()

            p = Path(td) / "mcp" / "credentials.json"
            self.assertTrue(p.exists())

            store2 = McpCredentialStore.load_default()
            merged = store2.merged_headers("srv", {"X": "1"})
            self.assertEqual(merged.get("X"), "1")
            self.assertEqual(merged.get("Authorization"), "Bearer t1")

            # Existing Authorization header should not be overridden.
            merged2 = store2.merged_headers("srv", {"Authorization": "Bearer other"})
            self.assertEqual(merged2.get("Authorization"), "Bearer other")


if __name__ == "__main__":
    unittest.main()
