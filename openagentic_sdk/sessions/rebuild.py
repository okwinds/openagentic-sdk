from __future__ import annotations

import json
from typing import Any, Mapping

from ..events import AssistantMessage, Event, ToolResult, ToolUse, UserMessage


def rebuild_messages(events: list[Event], *, max_events: int, max_bytes: int) -> list[Mapping[str, Any]]:
    messages_rev: list[Mapping[str, Any]] = []
    total_bytes = 0

    for e in reversed(events):
        msg: Mapping[str, Any] | None = None
        if isinstance(e, UserMessage):
            msg = {"role": "user", "content": e.text}
        elif isinstance(e, AssistantMessage):
            msg = {"role": "assistant", "content": e.text}
        elif isinstance(e, ToolUse):
            # Rebuild an assistant tool-call message so future provider calls that include tool results
            # remain valid for OpenAI-compatible gateways that require tool_call_id linkage.
            msg = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": e.tool_use_id,
                        "type": "function",
                        "function": {"name": e.name, "arguments": json.dumps(dict(e.input or {}), ensure_ascii=False)},
                    }
                ],
            }
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

    messages = list(reversed(messages_rev))

    # Safety: drop any tool results that don't have a preceding tool_calls entry in the reconstructed messages.
    # Some providers reject histories with unmatched tool_call_id.
    seen_tool_call_ids: set[str] = set()
    filtered: list[Mapping[str, Any]] = []
    for m in messages:
        if m.get("role") == "assistant" and isinstance(m.get("tool_calls"), list):
            for tc in m.get("tool_calls") or []:
                if isinstance(tc, dict):
                    tc_id = tc.get("id")
                    if isinstance(tc_id, str) and tc_id:
                        seen_tool_call_ids.add(tc_id)
            filtered.append(m)
            continue
        if m.get("role") == "tool":
            tc_id = m.get("tool_call_id")
            if isinstance(tc_id, str) and tc_id and tc_id in seen_tool_call_ids:
                filtered.append(m)
            continue
        filtered.append(m)

    return filtered


def rebuild_responses_input(events: list[Event], *, max_events: int, max_bytes: int) -> list[Mapping[str, Any]]:
    items_rev: list[Mapping[str, Any]] = []
    total_bytes = 0

    for e in reversed(events):
        item: Mapping[str, Any] | None = None
        if isinstance(e, UserMessage):
            item = {"role": "user", "content": e.text}
        elif isinstance(e, AssistantMessage):
            item = {"role": "assistant", "content": e.text}
        elif isinstance(e, ToolUse):
            item = {
                "type": "function_call",
                "call_id": e.tool_use_id,
                "name": e.name,
                "arguments": json.dumps(dict(e.input or {}), ensure_ascii=False),
            }
        elif isinstance(e, ToolResult):
            item = {
                "type": "function_call_output",
                "call_id": e.tool_use_id,
                "output": json.dumps(e.output, ensure_ascii=False),
            }

        if item is None:
            continue

        content = item.get("content") or item.get("output") or ""
        size = len(str(content).encode("utf-8"))
        if len(items_rev) >= max_events:
            break
        if total_bytes + size > max_bytes:
            break

        total_bytes += size
        items_rev.append(item)

    items = list(reversed(items_rev))

    seen_call_ids: set[str] = set()
    filtered: list[Mapping[str, Any]] = []
    for it in items:
        if it.get("type") == "function_call":
            call_id = it.get("call_id")
            if isinstance(call_id, str) and call_id:
                seen_call_ids.add(call_id)
            filtered.append(it)
            continue
        if it.get("type") == "function_call_output":
            call_id = it.get("call_id")
            if isinstance(call_id, str) and call_id and call_id in seen_call_ids:
                filtered.append(it)
            continue
        filtered.append(it)

    return filtered
