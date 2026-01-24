from __future__ import annotations

import inspect
import json
from dataclasses import asdict
from typing import Any, Mapping, Type

from . import events
from .errors import InvalidEventError, UnknownEventTypeError

_TYPE_MAP: Mapping[str, Type[events.EventBase]] = {
    "system.init": events.SystemInit,
    "user.message": events.UserMessage,
    "user.question": events.UserQuestion,
    "assistant.delta": events.AssistantDelta,
    "assistant.message": events.AssistantMessage,
    "tool.use": events.ToolUse,
    "tool.result": events.ToolResult,
    "hook.event": events.HookEvent,
    "result": events.Result,
}


def event_to_dict(event: events.Event) -> dict[str, Any]:
    return asdict(event)


def event_from_dict(obj: Mapping[str, Any]) -> events.Event:
    event_type = obj.get("type")
    if not isinstance(event_type, str) or not event_type:
        raise InvalidEventError("event missing valid 'type'")
    cls = _TYPE_MAP.get(event_type)
    if cls is None:
        raise UnknownEventTypeError(event_type)
    kwargs = dict(obj)
    kwargs.pop("type", None)
    allowed = set(inspect.signature(cls).parameters.keys())
    kwargs = {k: v for k, v in kwargs.items() if k in allowed}
    # dataclasses with default "type" accept kwargs without it
    try:
        return cls(**kwargs)  # type: ignore[arg-type]
    except TypeError as e:  # missing/extra fields, etc
        raise InvalidEventError(str(e)) from e


def dumps_event(event: events.Event) -> str:
    return json.dumps(event_to_dict(event), ensure_ascii=False, separators=(",", ":"))


def loads_event(raw: str) -> events.Event:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise InvalidEventError(str(e)) from e
    if not isinstance(obj, dict):
        raise InvalidEventError("event must be a JSON object")
    return event_from_dict(obj)
