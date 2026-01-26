from __future__ import annotations

import json
import threading
import time
import urllib.request
from pathlib import Path

from _common import repo_root, rightcode_options, run_sync
from openagentic_sdk.server.http_server import OpenAgenticHttpServer


def _http_json(url: str, method: str, payload: dict | None = None) -> object:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
        raw = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace"))


def _http_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


async def main() -> None:
    root = repo_root()
    options = rightcode_options(
        cwd=root,
        project_dir=root,
        allowed_tools=None,
        permission_mode="bypass",
        interactive=True,
    )

    httpd = OpenAgenticHttpServer(options=options, host="127.0.0.1", port=0).serve_forever()
    port = int(httpd.server_address[1])
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    base = f"http://127.0.0.1:{port}"
    try:
        html = _http_text(base + "/app")
        assert "openagentic-sdk" in html
        print(f"/app OK ({len(html)} bytes)")

        resp = _http_json(base + "/tui/append-prompt", "POST", {"text": "hi"})
        assert isinstance(resp, dict) and resp.get("ok") is True
        sid = resp.get("session_id")
        assert isinstance(sid, str) and sid
        print(f"/tui/append-prompt OK (session_id={sid})")

        # Wait until the async prompt produces at least one assistant message.
        deadline = time.time() + 15.0
        saw = False
        while time.time() < deadline:
            evs = _http_json(base + f"/session/{sid}/events", "GET")
            events = evs.get("events") if isinstance(evs, dict) else None
            if isinstance(events, list) and any(isinstance(e, dict) and e.get("type") == "assistant.message" for e in events):
                saw = True
                break
            time.sleep(0.1)
        assert saw
        print("assistant.message observed via /session/{id}/events")
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    # Usage:
    #   export RIGHTCODE_API_KEY=...
    #   python3 example/54_vscode_server_compat_smoke.py
    # Offline smoke:
    #   OPENAGENTIC_SDK_EXAMPLE_OFFLINE=1 python3 example/54_vscode_server_compat_smoke.py
    run_sync(main())
