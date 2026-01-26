from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


class TestLspClientLifecycleAndDiagnostics(unittest.IsolatedAsyncioTestCase):
    async def test_touch_uses_didchange_after_first_open_and_sends_watched_files(self) -> None:
        from openagentic_sdk.lsp.client import StdioLspClient

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Path(__file__).resolve().parent / "fixtures" / "lsp_stub_server.py"
            self.assertTrue(fixture.exists())

            f = root / "a.py"
            f.write_text("print('hi')\n", encoding="utf-8")

            c = StdioLspClient(command=[sys.executable, str(fixture)], cwd=str(root))
            try:
                await c.ensure_initialized(root_path=str(root))

                uri = await c.touch_file(str(f))
                h1 = await c.request_hover(uri=uri, line0=0, character0=0)
                s1 = str(h1)
                self.assertIn("stub hover", s1)
                self.assertIn("last=didOpen", s1)
                self.assertIn("watched=", s1)

                # Modify file and touch again: should use didChange + watched files.
                f.write_text("print('bye')\n", encoding="utf-8")
                uri2 = await c.touch_file(str(f))
                self.assertEqual(uri2, uri)
                h2 = await c.request_hover(uri=uri2, line0=0, character0=0)
                s2 = str(h2)
                self.assertIn("last=didChange", s2)
                # At least one watched-files notification should have been emitted.
                self.assertNotIn("watched=0", s2)
            finally:
                await c.close()

    async def test_wait_for_diagnostics_helper_exists(self) -> None:
        from openagentic_sdk.lsp.client import StdioLspClient

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Path(__file__).resolve().parent / "fixtures" / "lsp_stub_server.py"
            f = root / "a.py"
            f.write_text("print('hi')\n", encoding="utf-8")

            c = StdioLspClient(command=[sys.executable, str(fixture)], cwd=str(root))
            try:
                await c.ensure_initialized(root_path=str(root))
                await c.touch_file(str(f))

                # OpenCode parity: client provides a wait-for-diagnostics helper with debounce.
                wait = getattr(c, "wait_for_diagnostics")
                await wait(file_path=str(f), timeout_s=1.0)
            finally:
                await c.close()


if __name__ == "__main__":
    unittest.main()
