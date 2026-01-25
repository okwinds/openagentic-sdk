import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class _DummyClient:
    created = 0

    def __init__(self, command, cwd, environment=None, initialization_options=None, **kwargs):  # noqa: ANN001
        _ = (command, cwd, environment, initialization_options, kwargs)
        type(self).created += 1

    async def ensure_initialized(self, *, root_path, initialization_options=None):  # noqa: ANN001
        _ = (root_path, initialization_options)
        return None

    async def close(self):
        return None


class _FailingClient(_DummyClient):
    async def ensure_initialized(self, *, root_path, initialization_options=None):  # noqa: ANN001
        _ = (root_path, initialization_options)
        raise RuntimeError("boom")


class TestLspManagerCachingAndBroken(unittest.IsolatedAsyncioTestCase):
    async def test_caches_client_per_root_and_server(self) -> None:
        from openagentic_sdk.lsp.manager import LspManager

        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("print('hi')\n", encoding="utf-8")
            cfg = {
                "lsp": {
                    "pyright": {"disabled": True},
                    "stub": {"command": ["stub"], "extensions": [".py"]},
                }
            }

            _DummyClient.created = 0
            with patch("openagentic_sdk.lsp.manager.StdioLspClient", _DummyClient):
                async with LspManager(cfg=cfg, project_root=str(root)) as mgr:
                    pairs1 = await mgr.clients_for_file(str(root / "a.py"))
                    pairs2 = await mgr.clients_for_file(str(root / "a.py"))

                self.assertTrue(pairs1)
                self.assertTrue(pairs2)
                self.assertEqual(_DummyClient.created, 1)

    async def test_marks_broken_and_does_not_retry(self) -> None:
        from openagentic_sdk.lsp.manager import LspManager

        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.py").write_text("print('hi')\n", encoding="utf-8")
            cfg = {
                "lsp": {
                    "pyright": {"disabled": True},
                    "stub": {"command": ["stub"], "extensions": [".py"]},
                }
            }

            _FailingClient.created = 0
            with patch("openagentic_sdk.lsp.manager.StdioLspClient", _FailingClient):
                async with LspManager(cfg=cfg, project_root=str(root)) as mgr:
                    pairs1 = await mgr.clients_for_file(str(root / "a.py"))
                    pairs2 = await mgr.clients_for_file(str(root / "a.py"))

                self.assertEqual(pairs1, [])
                self.assertEqual(pairs2, [])
                self.assertEqual(_FailingClient.created, 1)


if __name__ == "__main__":
    unittest.main()
