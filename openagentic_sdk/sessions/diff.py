from __future__ import annotations

import difflib
from typing import Any, Mapping, Sequence


def transcript_from_messages(messages: Sequence[Mapping[str, Any]]) -> str:
    """Render a minimal, stable transcript suitable for diffing."""

    parts: list[str] = []
    for m in messages:
        if not isinstance(m, Mapping):
            continue
        role = m.get("role")
        content = m.get("content")
        if not isinstance(role, str):
            role = "?"
        if content is None:
            content_s = ""
        else:
            content_s = str(content)
        parts.append(f"[{role}]\n{content_s}\n")
    return "\n".join(parts).strip() + "\n"


def unified_diff(a: str, b: str, *, fromfile: str = "before", tofile: str = "after") -> str:
    a_lines = a.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)
    return "".join(difflib.unified_diff(a_lines, b_lines, fromfile=fromfile, tofile=tofile))
