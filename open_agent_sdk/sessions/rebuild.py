from __future__ import annotations

import json
from typing import Any, Mapping

from ..events import AssistantMessage, Event, ToolResult, UserMessage


def rebuild_messages(events: list[Event], *, max_events: int, max_bytes: int) -> list[Mapping[str, Any]]:
    messages_rev: list[Mapping[str, Any]] = []
    total_bytes = 0

    for e in reversed(events):
        msg: Mapping[str, Any] | None = None
        if isinstance(e, UserMessage):
            msg = {"role": "user", "content": e.text}
        elif isinstance(e, AssistantMessage):
            msg = {"role": "assistant", "content": e.text}
        elif isinstance(e, ToolResult):
            msg = {
                "role": "tool",
                "tool_call_id": e.tool_use_id,
                "content": json.dumps(e.output, ensure_ascii=False),
            }

        if msg is None:
            continue

        content = msg.get("content") or ""
        size = len(str(content).encode("utf-8"))
        if len(messages_rev) >= max_events:
            break
        if total_bytes + size > max_bytes:
            break

        total_bytes += size
        messages_rev.append(msg)

    return list(reversed(messages_rev))
