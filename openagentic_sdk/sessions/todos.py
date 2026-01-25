from __future__ import annotations

import hashlib
from typing import Any


def normalize_todos_for_api(raw: Any) -> list[dict[str, Any]]:
    """Normalize a persisted todo list to OpenCode's Todo.Info[] shape.

    OpenCode expects items like:
      {content, status, priority, id}

    We accept both:
    - OpenCode shape (already normalized)
    - legacy `TodoWrite` shape used earlier in this repo:
        {content, activeForm, status}
    """

    if not isinstance(raw, list):
        return []

    out: list[dict[str, Any]] = []
    for i, t in enumerate(raw):
        if not isinstance(t, dict):
            continue

        content = t.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        content2 = content.strip()

        status = t.get("status")
        status2 = status if isinstance(status, str) else "pending"
        if status2 not in ("pending", "in_progress", "completed", "cancelled"):
            status2 = "pending"

        priority = t.get("priority")
        pr2 = priority if isinstance(priority, str) else "medium"
        if pr2 not in ("low", "medium", "high"):
            pr2 = "medium"

        tid = t.get("id")
        if not isinstance(tid, str) or not tid.strip():
            # Deterministic id so read-after-write is stable when callers omit ids.
            h = hashlib.sha256(f"{content2}\n{i}".encode("utf-8")).hexdigest()
            tid2 = f"todo_{h[:16]}"
        else:
            tid2 = tid.strip()

        out.append({"content": content2, "status": status2, "priority": pr2, "id": tid2})

    return out
