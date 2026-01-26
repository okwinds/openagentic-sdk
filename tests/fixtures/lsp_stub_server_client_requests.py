from __future__ import annotations

import json
import sys


def _encode(obj: dict) -> bytes:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def _read_message() -> dict:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            raise EOFError
        if line in (b"\r\n", b"\n"):
            break
        try:
            k, v = line.decode("utf-8", errors="replace").split(":", 1)
            headers[k.strip().lower()] = v.strip()
        except ValueError:
            continue
    n = int(headers.get("content-length", "0") or "0")
    if n <= 0:
        raise ValueError("missing Content-Length")
    body = sys.stdin.buffer.read(n)
    obj = json.loads(body.decode("utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError("message must be object")
    return obj


def _send(obj: dict) -> None:
    sys.stdout.buffer.write(_encode(obj))
    sys.stdout.buffer.flush()


def main() -> int:
    while True:
        try:
            msg = _read_message()
        except EOFError:
            return 0

        method = msg.get("method")
        rid = msg.get("id")

        def respond(result: object) -> None:
            if isinstance(rid, int):
                _send({"jsonrpc": "2.0", "id": rid, "result": result})

        if method == "initialize":
            # Send a server->client request and require a response BEFORE replying
            # to initialize. This exercises client request handling.
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": 99,
                    "method": "workspace/configuration",
                    "params": {"items": [{"section": "stub"}]},
                }
            )

            # Wait for response id 99.
            while True:
                m2 = _read_message()
                if m2.get("id") == 99 and "result" in m2:
                    break

            respond({"capabilities": {"hoverProvider": True}})
            continue

        if method == "initialized":
            continue

        if isinstance(rid, int):
            _send({"jsonrpc": "2.0", "id": rid, "result": None})


if __name__ == "__main__":
    raise SystemExit(main())
