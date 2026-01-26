import json
import os
import threading
import unittest
from unittest import mock
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory


class _WellKnownHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/.well-known/opencode":
            body = json.dumps({"config": {"model": "wk", "instructions": ["x"]}}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt, *args):  # noqa: ANN001
        return


class TestOpenCodeConfigPrecedenceAndPacks(unittest.TestCase):
    def test_precedence_and_directory_pack_overrides_inline(self) -> None:
        from openagentic_sdk.auth import WellKnownAuth, set_auth
        from openagentic_sdk.opencode_config import load_merged_config

        with TemporaryDirectory() as td:
            root = Path(td)
            global_dir = root / "global"
            global_dir.mkdir(parents=True)
            (global_dir / "opencode.json").write_text('{"model": "global", "instructions": ["a"]}\n', encoding="utf-8")

            project_root = root / "proj"
            (project_root / ".git").mkdir(parents=True)
            cwd = project_root / "sub"
            cwd.mkdir(parents=True)

            # Project config (opencode.json/jsonc) layer.
            (project_root / "opencode.json").write_text('{"model": "project", "instructions": ["c"]}\n', encoding="utf-8")

            # OPENCODE_CONFIG layer.
            custom_path = root / "custom.json"
            custom_path.write_text('{"model": "custom", "instructions": ["b"]}\n', encoding="utf-8")

            # Directory pack layer (scanned after OPENCODE_CONFIG_CONTENT).
            pack = project_root / ".opencode"
            pack.mkdir(parents=True)
            (pack / "opencode.json").write_text('{"model": "dirpack", "instructions": ["e"]}\n', encoding="utf-8")

            httpd = ThreadingHTTPServer(("127.0.0.1", 0), _WellKnownHandler)
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            base = f"http://127.0.0.1:{httpd.server_address[1]}"

            env = {
                "OPENCODE_TEST_HOME": str(root / "home"),
                "OPENAGENTIC_SDK_HOME": str(root / "home"),
                "OPENCODE_CONFIG": str(custom_path),
                "OPENCODE_CONFIG_CONTENT": '{"model": "inline", "instructions": ["d"]}',
            }
            with mock.patch.dict(os.environ, env, clear=False):
                try:
                    set_auth(base, WellKnownAuth(key="WK_TOKEN", token="secret"))

                    cfg = load_merged_config(cwd=str(cwd), global_config_dir=str(global_dir))
                    # Directory packs are applied after OPENCODE_CONFIG_CONTENT.
                    self.assertEqual(cfg.get("model"), "dirpack")
                    # Only `instructions` is concatenated across layers.
                    self.assertEqual(cfg.get("instructions"), ["x", "a", "b", "c", "d", "e"])
                finally:
                    try:
                        httpd.shutdown()
                        httpd.server_close()
                    except Exception:  # noqa: BLE001
                        pass
                    os.environ.pop("WK_TOKEN", None)

    def test_directory_pack_markdown_and_plugins_loaded(self) -> None:
        from openagentic_sdk.opencode_config import load_merged_config

        with TemporaryDirectory() as td:
            root = Path(td)
            (root / ".git").mkdir()
            (root / "sub").mkdir()

            pack = root / ".opencode"
            (pack / "commands" / "nested").mkdir(parents=True)
            (pack / "agents").mkdir(parents=True)
            (pack / "modes").mkdir(parents=True)
            (pack / "plugins").mkdir(parents=True)

            (pack / "commands" / "nested" / "hello.md").write_text(
                "---\ndescription: hi\n---\n\nHello body\n",
                encoding="utf-8",
            )
            (pack / "agents" / "a.md").write_text(
                "---\ndescription: agent\n---\n\nAgent prompt\n",
                encoding="utf-8",
            )
            (pack / "modes" / "m.md").write_text(
                "---\ndescription: mode\n---\n\nMode prompt\n",
                encoding="utf-8",
            )
            (pack / "plugins" / "p.ts").write_text("// plugin", encoding="utf-8")

            env = {
                "OPENCODE_TEST_HOME": str(root / "home"),
                "OPENAGENTIC_SDK_HOME": str(root / "home"),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                cfg = load_merged_config(cwd=str(root / "sub"), global_config_dir=str(root / "empty-global"))

            cmd = cfg.get("command") or {}
            self.assertIn("nested/hello", cmd)
            self.assertEqual(cmd["nested/hello"].get("template"), "Hello body")
            self.assertEqual(cmd["nested/hello"].get("description"), "hi")

            agent = cfg.get("agent") or {}
            self.assertIn("a", agent)
            self.assertEqual(agent["a"].get("prompt"), "Agent prompt")

            # Modes are merged into `agent` in OpenCode (mode -> agent primary).
            self.assertIn("m", agent)
            self.assertEqual(agent["m"].get("prompt"), "Mode prompt")

            plugins = cfg.get("plugin") or []
            self.assertTrue(any(isinstance(p, str) and p.startswith("file://") and p.endswith("/p.ts") for p in plugins))

    def test_schema_insertion_writeback_preserves_env_tokens(self) -> None:
        from openagentic_sdk.opencode_config import load_config_file

        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "opencode.jsonc"
            p.write_text('{"x": "{env:OA_TEST_ENV}"}\n', encoding="utf-8")
            os.environ["OA_TEST_ENV"] = "ENVVAL"
            try:
                cfg = load_config_file(str(p))
                self.assertEqual(cfg.get("x"), "ENVVAL")
                self.assertEqual(cfg.get("$schema"), "https://opencode.ai/config.json")

                # File should now contain $schema but still keep the literal env token.
                updated = p.read_text(encoding="utf-8", errors="replace")
                self.assertIn('"$schema": "https://opencode.ai/config.json"', updated)
                self.assertIn("{env:OA_TEST_ENV}", updated)
            finally:
                os.environ.pop("OA_TEST_ENV", None)

    def test_plugin_canonical_dedupe_later_wins(self) -> None:
        from openagentic_sdk.opencode_config import load_merged_config

        with TemporaryDirectory() as td:
            root = Path(td)
            global_dir = root / "global"
            global_dir.mkdir(parents=True)
            (global_dir / "opencode.json").write_text('{"plugin": ["foo@1.0.0", "bar@1.0.0"]}\n', encoding="utf-8")

            project = root / "proj" / "sub"
            project.mkdir(parents=True)
            (root / "proj" / "opencode.json").write_text('{"plugin": ["foo@2.0.0"]}\n', encoding="utf-8")

            os.environ["OPENCODE_TEST_HOME"] = str(root / "home")
            try:
                cfg = load_merged_config(cwd=str(project), global_config_dir=str(global_dir))
                self.assertEqual(cfg.get("plugin"), ["bar@1.0.0", "foo@2.0.0"])
            finally:
                os.environ.pop("OPENCODE_TEST_HOME", None)


if __name__ == "__main__":
    unittest.main()
