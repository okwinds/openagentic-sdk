import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from tempfile import TemporaryDirectory


class _Handler(BaseHTTPRequestHandler):
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


class TestWellKnownConfig(unittest.TestCase):
    def test_loads_remote_wellknown_config_lowest_precedence(self) -> None:
        from openagentic_sdk.auth import WellKnownAuth, set_auth
        from openagentic_sdk.opencode_config import load_merged_config

        with TemporaryDirectory() as td:
            os.environ["OPENCODE_TEST_HOME"] = td
            os.environ["OPENAGENTIC_SDK_HOME"] = td
            os.environ["OPENCODE_DISABLE_PROJECT_CONFIG"] = "1"
            try:
                httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
                t = threading.Thread(target=httpd.serve_forever, daemon=True)
                t.start()
                base = f"http://127.0.0.1:{httpd.server_address[1]}"

                # Store well-known auth entry.
                set_auth(base, WellKnownAuth(key="WK_TOKEN", token="secret"))

                cfg = load_merged_config(cwd=td, global_config_dir=td)
                self.assertEqual(cfg.get("model"), "wk")
                self.assertEqual(cfg.get("instructions"), ["x"])
            finally:
                try:
                    httpd.shutdown()
                    httpd.server_close()
                except Exception:  # noqa: BLE001
                    pass
                os.environ.pop("OPENCODE_TEST_HOME", None)
                os.environ.pop("OPENAGENTIC_SDK_HOME", None)
                os.environ.pop("OPENCODE_DISABLE_PROJECT_CONFIG", None)
                os.environ.pop("WK_TOKEN", None)


if __name__ == "__main__":
    unittest.main()
