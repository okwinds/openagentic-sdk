from __future__ import annotations

from collections.abc import Iterable, Iterator


def parse_sse_events(lines: Iterable[bytes]) -> Iterator[str]:
    buf: list[str] = []
    for raw in lines:
        line = raw.decode("utf-8", errors="replace")
        if line in ("\n", "\r\n"):
            if buf:
                yield "".join(buf)
                buf = []
            continue
        if line.startswith("data:"):
            buf.append(line[len("data:") :].lstrip().rstrip("\r\n"))
    if buf:
        yield "".join(buf)

