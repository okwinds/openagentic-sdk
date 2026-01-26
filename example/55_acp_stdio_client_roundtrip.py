from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from _common import repo_root, require_env


class _LineReader:
    def __init__(self, stream) -> None:  # noqa: ANN001
        self._q: queue.Queue[str] = queue.Queue()

        def _bg() -> None:
            for line in iter(stream.readline, ""):
                self._q.put(line)

        self._t = threading.Thread(target=_bg, daemon=True)
        self._t.start()

    def get(self, timeout_s: float) -> str | None:
        try:
            return self._q.get(timeout=timeout_s)
        except queue.Empty:
            return None


def _send(proc: subprocess.Popen[str], obj: dict) -> None:
    line = json.dumps(obj, ensure_ascii=False)
    stdin = proc.stdin
    if stdin is None:
        raise RuntimeError("stdin closed")
    stdin.write(line + "\n")
    stdin.flush()


def _read_json_line(reader: _LineReader, timeout_s: float) -> dict | None:
    line = reader.get(timeout_s)
    if line is None:
        return None
    line = line.strip()
    if not line:
        return None
    return json.loads(line)


def main() -> None:
    # This example runs a real ACP stdio server (`oa acp`) and speaks NDJSON
    # JSON-RPC as a tiny client.
    _ = require_env("RIGHTCODE_API_KEY")

    root = repo_root()
    env = dict(os.environ)
    env["PYTHONPATH"] = os.fspath(root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    proc = subprocess.Popen(
        [sys.executable, "-m", "openagentic_cli", "acp"],
        cwd=os.fspath(root),
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        assert proc.stdout is not None
        out = _LineReader(proc.stdout)

        _send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1"}})
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "session/new", "params": {"cwd": os.fspath(root), "mcpServers": []}})

        session_id = None
        updates = 0
        deadline = time.time() + 10.0

        while time.time() < deadline:
            msg = _read_json_line(out, timeout_s=0.25)
            if msg is None:
                continue
            if msg.get("method") == "session/update":
                updates += 1
                if updates <= 3:
                    print("update:", msg.get("params", {}).get("update"))
                continue
            if msg.get("id") == 1:
                print("initialize:", msg.get("result"))
                continue
            if msg.get("id") == 2:
                session_id = msg.get("result", {}).get("sessionId")
                print("session/new:", session_id)
                break

        if not isinstance(session_id, str) or not session_id:
            raise SystemExit("did not get sessionId")

        # Send a prompt. If the agent requests permissions, we allow them.
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "session/prompt",
                "params": {"sessionId": session_id, "prompt": "Say hello in one short paragraph. Do not use tools."},
            },
        )

        deadline = time.time() + 30.0
        while time.time() < deadline:
            msg = _read_json_line(out, timeout_s=0.25)
            if msg is None:
                continue

            # Server->client permission request.
            if msg.get("method") == "session/request_permission" and isinstance(msg.get("id"), int):
                rid = int(msg["id"])
                _send(proc, {"jsonrpc": "2.0", "id": rid, "result": {"outcome": {"outcome": "selected", "optionId": "allow"}}})
                continue

            if msg.get("method") == "session/update":
                updates += 1
                continue
            if msg.get("id") == 3:
                print("session/prompt result:", msg.get("result"))
                break

        print(f"done (updates={updates})")
    finally:
        try:
            if proc.stdin is not None:
                proc.stdin.close()
        except Exception:
            pass
        try:
            if proc.stdout is not None:
                proc.stdout.close()
        except Exception:
            pass
        try:
            if proc.stderr is not None:
                proc.stderr.close()
        except Exception:
            pass
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
