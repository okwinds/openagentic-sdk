from __future__ import annotations

import asyncio
import json
from typing import Any, Mapping


def encode_message(obj: Mapping[str, Any]) -> bytes:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


async def read_message(stream: asyncio.StreamReader) -> Mapping[str, Any]:
    headers: dict[str, str] = {}
    while True:
        line = await stream.readline()
        if not line:
            raise EOFError("lsp: EOF")
        if line in (b"\r\n", b"\n"):
            break
        try:
            k, v = line.decode("utf-8", errors="replace").split(":", 1)
            headers[k.strip().lower()] = v.strip()
        except ValueError:
            continue
    n = int(headers.get("content-length", "0") or "0")
    if n <= 0:
        raise ValueError("lsp: missing Content-Length")
    body = await stream.readexactly(n)
    obj = json.loads(body.decode("utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError("lsp: message must be object")
    return obj
