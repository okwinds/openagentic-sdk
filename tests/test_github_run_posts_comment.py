from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory


class _Capture:
    def __init__(self) -> None:
        self.paths: list[str] = []
        self.bodies: list[dict] = []
        self.auth: list[str] = []


def _start_mock_github(capture: _Capture) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            capture.paths.append(self.path)
            capture.auth.append(self.headers.get("Authorization") or "")
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                obj = json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                obj = None
            capture.bodies.append(obj if isinstance(obj, dict) else {})

            self.send_response(201)
            out = json.dumps({"id": 1}).encode("utf-8")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, format, *args):  # noqa: A002,ANN001
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


class TestGithubRunPostsComment(unittest.TestCase):
    def test_posts_comment_when_mentioned(self) -> None:
        cap = _Capture()
        httpd = _start_mock_github(cap)
        port = int(httpd.server_address[1])
        try:
            with TemporaryDirectory() as td:
                root = Path(td)
                event_path = root / "event.json"
                event_path.write_text(
                    json.dumps(
                        {
                            "comment": {"body": "/oc please"},
                            "issue": {"number": 1, "title": "Bug"},
                        }
                    ),
                    encoding="utf-8",
                )

                env = dict(os.environ)
                repo_root = Path(__file__).resolve().parents[1]
                env["PYTHONPATH"] = os.fspath(repo_root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
                env["GITHUB_EVENT_NAME"] = "issue_comment"
                env["GITHUB_REPOSITORY"] = "o/a"
                env["GITHUB_RUN_ID"] = "1"
                env["MENTIONS"] = "/oc"

                proc = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "openagentic_cli",
                        "github",
                        "run",
                        "--event-path",
                        os.fspath(event_path),
                        "--reply-text",
                        "hi",
                        "--base-url",
                        f"http://127.0.0.1:{port}",
                        "--token",
                        "t",
                    ],
                    cwd=os.fspath(root),
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertIn("hi", proc.stdout)

                self.assertEqual(cap.paths, ["/repos/o/a/issues/1/comments"])
                self.assertEqual(cap.bodies, [{"body": "hi"}])
                self.assertTrue(cap.auth and cap.auth[0])
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_skips_when_not_mentioned(self) -> None:
        cap = _Capture()
        httpd = _start_mock_github(cap)
        port = int(httpd.server_address[1])
        try:
            with TemporaryDirectory() as td:
                root = Path(td)
                event_path = root / "event.json"
                event_path.write_text(
                    json.dumps(
                        {
                            "comment": {"body": "hello"},
                            "issue": {"number": 1, "title": "Bug"},
                        }
                    ),
                    encoding="utf-8",
                )

                env = dict(os.environ)
                repo_root = Path(__file__).resolve().parents[1]
                env["PYTHONPATH"] = os.fspath(repo_root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
                env["GITHUB_EVENT_NAME"] = "issue_comment"
                env["GITHUB_REPOSITORY"] = "o/a"
                env["GITHUB_RUN_ID"] = "1"
                env["MENTIONS"] = "/oc"

                proc = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "openagentic_cli",
                        "github",
                        "run",
                        "--event-path",
                        os.fspath(event_path),
                        "--reply-text",
                        "hi",
                        "--base-url",
                        f"http://127.0.0.1:{port}",
                        "--token",
                        "t",
                    ],
                    cwd=os.fspath(root),
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertIn("skipped", proc.stdout)
                self.assertEqual(cap.paths, [])
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
