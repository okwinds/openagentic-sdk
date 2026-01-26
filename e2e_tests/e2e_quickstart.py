from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import openagentic_sdk

from e2e_tests._harness import make_options


class TestE2EQuickstart(unittest.IsolatedAsyncioTestCase):
    async def test_run_returns_final_text_and_session(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            opts = make_options(root, allowed_tools=[])
            r = await openagentic_sdk.run(prompt="Reply with exactly: E2E_QUICKSTART_OK", options=opts)
            self.assertTrue(r.session_id)
            self.assertTrue((r.final_text or "").strip())


if __name__ == "__main__":
    unittest.main()

