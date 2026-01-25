from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..compaction import TOOL_OUTPUT_PLACEHOLDER
from ..events import (
    AssistantMessage,
    Event,
    ToolOutputCompacted,
    ToolResult,
    ToolUse,
    UserCompaction,
    UserMessage,
)

from ..sessions.rebuild import _filter_to_head  # type: ignore[attr-defined]


def _ms(ts_s: float | None) -> int | None:
    if ts_s is None:
        return None
    try:
        return int(float(ts_s) * 1000)
    except Exception:
        return None


def _collect_compacted_tool_ids(events: list[Event]) -> set[str]:
    out: set[str] = set()
    for e in events:
        if isinstance(e, ToolOutputCompacted):
            tid = getattr(e, "tool_use_id", "")
            if isinstance(tid, str) and tid:
                out.add(tid)
    return out


def build_message_v2(events: list[Event], *, session_id: str) -> list[dict[str, Any]]:
    """Build an OpenCode-like MessageV2 list from our append-only event log.

    This is a best-effort mapping:
    - We group tool.use/tool.result and assistant.message events into a single assistant message
      per user turn.
    - We preserve tool-output compaction via TOOL_OUTPUT_PLACEHOLDER.
    """

    events2 = _filter_to_head(events)
    compacted = _collect_compacted_tool_ids(events2)

    out: list[dict[str, Any]] = []
    current_user_id: str | None = None
    assistant_parts: list[dict[str, Any]] = []
    tool_parts_by_id: dict[str, dict[str, Any]] = {}
    assistant_summary = False
    assistant_ts: float | None = None
    assistant_seq: int | None = None

    def flush_assistant() -> None:
        nonlocal assistant_parts, tool_parts_by_id, assistant_summary, assistant_ts, assistant_seq
        if tool_parts_by_id:
            # Stable ordering by tool_use_id.
            for tid in sorted(tool_parts_by_id.keys()):
                assistant_parts.append(tool_parts_by_id[tid])
            tool_parts_by_id = {}
        if not assistant_parts:
            assistant_summary = False
            assistant_ts = None
            assistant_seq = None
            return
        mid = f"assistant_{assistant_seq or len(out) + 1}"
        out.append(
            {
                "info": {
                    "id": mid,
                    "sessionID": session_id,
                    "role": "assistant",
                    "parentID": current_user_id,
                    "summary": bool(assistant_summary),
                    "finish": True,
                    "time": {"created": _ms(assistant_ts)},
                },
                "parts": assistant_parts,
            }
        )
        assistant_parts = []
        assistant_summary = False
        assistant_ts = None
        assistant_seq = None

    for e in events2:
        if isinstance(e, (UserMessage, UserCompaction)):
            flush_assistant()
            seq = getattr(e, "seq", None)
            current_user_id = f"user_{seq or len(out) + 1}"
            if isinstance(e, UserCompaction):
                out.append(
                    {
                        "info": {
                            "id": current_user_id,
                            "sessionID": session_id,
                            "role": "user",
                            "time": {"created": _ms(getattr(e, "ts", None))},
                        },
                        "parts": [{"type": "compaction", "auto": bool(getattr(e, "auto", False))}],
                    }
                )
            else:
                out.append(
                    {
                        "info": {
                            "id": current_user_id,
                            "sessionID": session_id,
                            "role": "user",
                            "time": {"created": _ms(getattr(e, "ts", None))},
                        },
                        "parts": [{"type": "text", "text": str(getattr(e, "text", ""))}],
                    }
                )
            continue

        if isinstance(e, ToolUse):
            tid = getattr(e, "tool_use_id", "")
            if not isinstance(tid, str) or not tid:
                continue
            tool_parts_by_id[tid] = {
                "type": "tool",
                "tool": str(getattr(e, "name", "")),
                "callID": tid,
                "state": {
                    "status": "running",
                    "input": dict(getattr(e, "input", None) or {}),
                },
            }
            continue

        if isinstance(e, ToolResult):
            tid = getattr(e, "tool_use_id", "")
            if not isinstance(tid, str) or not tid:
                continue
            part = tool_parts_by_id.get(tid) or {
                "type": "tool",
                "tool": "",
                "callID": tid,
                "state": {"status": "running", "input": {}},
            }
            out_text = TOOL_OUTPUT_PLACEHOLDER if tid in compacted else getattr(e, "output", None)
            state = part.get("state") if isinstance(part.get("state"), dict) else {}
            state2 = dict(state)
            if bool(getattr(e, "is_error", False)):
                state2.update({"status": "error", "error": getattr(e, "error_message", None), "output": out_text})
            else:
                state2.update({"status": "completed", "output": out_text})
            part["state"] = state2
            tool_parts_by_id[tid] = part
            continue

        if isinstance(e, AssistantMessage):
            assistant_summary = assistant_summary or bool(getattr(e, "is_summary", False))
            if assistant_ts is None:
                assistant_ts = getattr(e, "ts", None)
            assistant_seq = getattr(e, "seq", None)
            assistant_parts.append({"type": "text", "text": str(getattr(e, "text", ""))})
            continue

    flush_assistant()
    return out
