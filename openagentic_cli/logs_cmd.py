from __future__ import annotations

from collections import Counter, deque
from typing import Iterable

from openagentic_sdk.events import Event

from .style import StyleConfig, bold, dim, fg_green, fg_red, should_colorize


def summarize_events(
    events: Iterable[Event],
    *,
    color_config: StyleConfig | None = None,
    isatty: bool = False,
    platform: str = "linux",
) -> str:
    cfg = color_config or StyleConfig(color="auto")
    enable_color = should_colorize(cfg, isatty=isatty, platform=platform)

    counts: Counter[str] = Counter()
    recent_tool_lines: deque[str] = deque(maxlen=10)
    last_stop_reason: str | None = None

    tool_names: dict[str, str] = {}
    tool_results: dict[str, str] = {}

    for e in events:
        t = getattr(e, "type", None)
        if isinstance(t, str):
            counts[t] += 1

        if t == "tool.use":
            tool_use_id = str(getattr(e, "tool_use_id", "") or "")
            name = str(getattr(e, "name", "") or "")
            if tool_use_id:
                tool_names[tool_use_id] = name
        if t == "tool.result":
            tool_use_id = str(getattr(e, "tool_use_id", "") or "")
            is_error = bool(getattr(e, "is_error", False))
            tool_results[tool_use_id] = "error" if is_error else "ok"
        if t == "result":
            sr = getattr(e, "stop_reason", None)
            last_stop_reason = str(sr) if sr is not None else None

    for tool_use_id, name in list(tool_names.items())[-10:]:
        res = tool_results.get(tool_use_id)
        if res is None:
            recent_tool_lines.append(f"- {name} ({tool_use_id})")
        elif res == "ok":
            recent_tool_lines.append(f"- {name} ({tool_use_id}): ok")
        else:
            recent_tool_lines.append(f"- {name} ({tool_use_id}): error")

    lines: list[str] = []
    lines.append(bold("Event counts:", enabled=enable_color))
    for k in sorted(counts.keys()):
        lines.append(f"- {k}: {counts[k]}")

    if recent_tool_lines:
        lines.append("")
        lines.append(bold("Recent tools:", enabled=enable_color))
        lines.extend(list(recent_tool_lines))

    if last_stop_reason is not None:
        lines.append("")
        lines.append(
            dim("Last stop_reason: ", enabled=enable_color)
            + (fg_green(last_stop_reason, enabled=enable_color) if last_stop_reason else fg_red("unknown", enabled=enable_color))
        )

    return "\n".join(lines).rstrip() + "\n"

