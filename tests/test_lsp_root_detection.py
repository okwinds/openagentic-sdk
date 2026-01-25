import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestLspRootDetection(unittest.TestCase):
    def test_nearest_root_fallbacks_to_workspace(self) -> None:
        from openagentic_sdk.lsp.registry import builtin_servers

        with TemporaryDirectory() as td:
            ws = Path(td)
            (ws / "src").mkdir()
            f = ws / "src" / "a.ts"
            f.write_text("export const x = 1\n", encoding="utf-8")

            reg = builtin_servers(workspace_dir=ws)
            ts = reg["typescript"]
            root = ts.root(str(f))

            # With no lockfiles, OpenCode's NearestRoot falls back to workspace.
            self.assertEqual(Path(root or "").resolve(), ws.resolve())

    def test_nearest_root_exclude_disables(self) -> None:
        from openagentic_sdk.lsp.registry import builtin_servers

        with TemporaryDirectory() as td:
            ws = Path(td)
            (ws / "deno.json").write_text("{}\n", encoding="utf-8")
            f = ws / "a.ts"
            f.write_text("export const x = 1\n", encoding="utf-8")

            reg = builtin_servers(workspace_dir=ws)
            ts = reg["typescript"]
            # Typescript server excludes deno projects.
            self.assertIsNone(ts.root(str(f)))

    def test_required_root_returns_none(self) -> None:
        from openagentic_sdk.lsp.registry import builtin_servers

        with TemporaryDirectory() as td:
            ws = Path(td)
            f = ws / "a.ts"
            f.write_text("export const x = 1\n", encoding="utf-8")
            reg = builtin_servers(workspace_dir=ws)
            deno = reg["deno"]
            self.assertIsNone(deno.root(str(f)))

    def test_workspace_root_servers(self) -> None:
        from openagentic_sdk.lsp.registry import builtin_servers

        with TemporaryDirectory() as td:
            ws = Path(td)
            f = ws / "Dockerfile"
            f.write_text("FROM scratch\n", encoding="utf-8")
            reg = builtin_servers(workspace_dir=ws)
            docker = reg["dockerfile"]
            self.assertEqual(Path(docker.root(str(f)) or "").resolve(), ws.resolve())


if __name__ == "__main__":
    unittest.main()
