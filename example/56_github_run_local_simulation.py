from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import repo_root


class _Capture:
    def __init__(self) -> None:
        self.paths: list[str] = []
        self.bodies: list[dict] = []


def _start_mock_github(capture: _Capture) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            capture.paths.append(self.path)
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


def main() -> None:
    root = repo_root()
    cap = _Capture()
    httpd = _start_mock_github(cap)
    port = int(httpd.server_address[1])

    try:
        with TemporaryDirectory() as td:
            work = Path(td)
            event_path = work / "event.json"
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
            env["PYTHONPATH"] = os.fspath(root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            env["GITHUB_EVENT_NAME"] = "issue_comment"
            env["GITHUB_REPOSITORY"] = "o/a"
            env["GITHUB_RUN_ID"] = "1"

            cmd = [
                sys.executable,
                "-m",
                "openagentic_cli",
                "github",
                "run",
                "--event-path",
                os.fspath(event_path),
                "--reply-text",
                "Hello from openagentic-sdk",
                "--base-url",
                f"http://127.0.0.1:{port}",
                "--token",
                "t",
                "--mentions",
                "/oc",
            ]
            proc = subprocess.run(cmd, cwd=os.fspath(work), env=env, check=True, capture_output=True, text=True)
            print(proc.stdout.strip())

            print("mock github received:")
            print(cap.paths)
            print(cap.bodies)
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
