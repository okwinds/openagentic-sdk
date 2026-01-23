from __future__ import annotations

import fnmatch
import time
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..events import HookEvent
from .models import HookDecision, HookMatcher


def _match_name(pattern: str, name: str) -> bool:
    for seg in pattern.split("|"):
        if fnmatch.fnmatchcase(name, seg.strip()):
            return True
    return False


@dataclass(frozen=True, slots=True)
class HookEngine:
    pre_tool_use: Sequence[HookMatcher] = ()
    post_tool_use: Sequence[HookMatcher] = ()
    before_model_call: Sequence[HookMatcher] = ()
    after_model_call: Sequence[HookMatcher] = ()
    session_start: Sequence[HookMatcher] = ()
    session_end: Sequence[HookMatcher] = ()
    stop: Sequence[HookMatcher] = ()
    enable_message_rewrite_hooks: bool = False

    async def run_pre_tool_use(
        self,
        *,
        tool_name: str,
        tool_input: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], list[HookEvent], HookDecision | None]:
        current_input: Mapping[str, Any] = tool_input
        hook_events: list[HookEvent] = []
        for matcher in self.pre_tool_use:
            matched = _match_name(matcher.tool_name_pattern, tool_name)
            started = time.time()
            decision: HookDecision | None = None
            action: str | None = None
            if matched and matcher.hook is not None:
                decision = await matcher.hook(
                    {
                        "tool_name": tool_name,
                        "tool_input": dict(current_input),
                        "context": dict(context),
                        "hook_point": "PreToolUse",
                    }
                )
                action = decision.action
                if decision.block:
                    hook_events.append(
                        HookEvent(
                            hook_point="PreToolUse",
                            name=matcher.name,
                            matched=True,
                            duration_ms=(time.time() - started) * 1000,
                            action=action or "block",
                        )
                    )
                    return current_input, hook_events, decision
                if decision.override_tool_input is not None:
                    current_input = decision.override_tool_input
                    action = action or "rewrite_tool_input"
            hook_events.append(
                HookEvent(
                    hook_point="PreToolUse",
                    name=matcher.name,
                    matched=matched,
                    duration_ms=(time.time() - started) * 1000,
                    action=action,
                )
            )
        return current_input, hook_events, None

    async def run_post_tool_use(
        self,
        *,
        tool_name: str,
        tool_output: Any,
        context: Mapping[str, Any],
    ) -> tuple[Any, list[HookEvent], HookDecision | None]:
        current_output: Any = tool_output
        hook_events: list[HookEvent] = []
        for matcher in self.post_tool_use:
            matched = _match_name(matcher.tool_name_pattern, tool_name)
            started = time.time()
            decision: HookDecision | None = None
            action: str | None = None
            if matched and matcher.hook is not None:
                decision = await matcher.hook(
                    {
                        "tool_name": tool_name,
                        "tool_output": current_output,
                        "context": dict(context),
                        "hook_point": "PostToolUse",
                    }
                )
                action = decision.action
                if decision.block:
                    hook_events.append(
                        HookEvent(
                            hook_point="PostToolUse",
                            name=matcher.name,
                            matched=True,
                            duration_ms=(time.time() - started) * 1000,
                            action=action or "block",
                        )
                    )
                    return current_output, hook_events, decision
                if decision.override_tool_output is not None:
                    current_output = decision.override_tool_output
                    action = action or "rewrite_tool_output"
            hook_events.append(
                HookEvent(
                    hook_point="PostToolUse",
                    name=matcher.name,
                    matched=matched,
                    duration_ms=(time.time() - started) * 1000,
                    action=action,
                )
            )
        return current_output, hook_events, None

    async def run_before_model_call(
        self, *, messages: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
    ) -> tuple[list[Mapping[str, Any]], list[HookEvent], HookDecision | None]:
        current_messages = [dict(m) for m in messages]
        hook_events: list[HookEvent] = []
        model = context.get("model")
        match_target = model if isinstance(model, str) else ""
        for matcher in self.before_model_call:
            matched = _match_name(matcher.tool_name_pattern, match_target)
            started = time.time()
            decision: HookDecision | None = None
            action: str | None = None
            if matched and matcher.hook is not None:
                decision = await matcher.hook(
                    {
                        "messages": list(current_messages),
                        "context": dict(context),
                        "hook_point": "BeforeModelCall",
                    }
                )
                action = decision.action
                if decision.block:
                    hook_events.append(
                        HookEvent(
                            hook_point="BeforeModelCall",
                            name=matcher.name,
                            matched=True,
                            duration_ms=(time.time() - started) * 1000,
                            action=action or "block",
                        )
                    )
                    return current_messages, hook_events, decision
                if decision.override_messages is not None:
                    if self.enable_message_rewrite_hooks:
                        current_messages = [dict(m) for m in decision.override_messages]
                        action = action or "rewrite_messages"
                    else:
                        action = action or "ignored_override_messages"
                        decision = None
            hook_events.append(
                HookEvent(
                    hook_point="BeforeModelCall",
                    name=matcher.name,
                    matched=matched,
                    duration_ms=(time.time() - started) * 1000,
                    action=action,
                )
            )
        return current_messages, hook_events, None

    async def run_after_model_call(
        self, *, output: Any, context: Mapping[str, Any]
    ) -> tuple[Any, list[HookEvent], HookDecision | None]:
        current_output: Any = output
        hook_events: list[HookEvent] = []
        model = context.get("model")
        match_target = model if isinstance(model, str) else ""
        for matcher in self.after_model_call:
            matched = _match_name(matcher.tool_name_pattern, match_target)
            started = time.time()
            decision: HookDecision | None = None
            action: str | None = None
            if matched and matcher.hook is not None:
                decision = await matcher.hook(
                    {
                        "output": current_output,
                        "context": dict(context),
                        "hook_point": "AfterModelCall",
                    }
                )
                action = decision.action
                if decision.block:
                    hook_events.append(
                        HookEvent(
                            hook_point="AfterModelCall",
                            name=matcher.name,
                            matched=True,
                            duration_ms=(time.time() - started) * 1000,
                            action=action or "block",
                        )
                    )
                    return current_output, hook_events, decision
                if decision.override_tool_output is not None:
                    current_output = decision.override_tool_output
                    action = action or "rewrite_model_output"
            hook_events.append(
                HookEvent(
                    hook_point="AfterModelCall",
                    name=matcher.name,
                    matched=matched,
                    duration_ms=(time.time() - started) * 1000,
                    action=action,
                )
            )
        return current_output, hook_events, None

    async def run_session_start(self, *, context: Mapping[str, Any]) -> list[HookEvent]:
        hook_events: list[HookEvent] = []
        for matcher in self.session_start:
            started = time.time()
            matched = True
            action: str | None = None
            if matcher.hook is not None:
                decision = await matcher.hook({"context": dict(context), "hook_point": "SessionStart"})
                action = decision.action
                if decision.block:
                    action = action or "block"
            hook_events.append(
                HookEvent(
                    hook_point="SessionStart",
                    name=matcher.name,
                    matched=matched,
                    duration_ms=(time.time() - started) * 1000,
                    action=action,
                )
            )
        return hook_events

    async def run_session_end(self, *, context: Mapping[str, Any]) -> list[HookEvent]:
        hook_events: list[HookEvent] = []
        for matcher in self.session_end:
            started = time.time()
            matched = True
            action: str | None = None
            if matcher.hook is not None:
                decision = await matcher.hook({"context": dict(context), "hook_point": "SessionEnd"})
                action = decision.action
                if decision.block:
                    action = action or "block"
            hook_events.append(
                HookEvent(
                    hook_point="SessionEnd",
                    name=matcher.name,
                    matched=matched,
                    duration_ms=(time.time() - started) * 1000,
                    action=action,
                )
            )
        return hook_events

    async def run_stop(self, *, final_text: str, context: Mapping[str, Any]) -> list[HookEvent]:
        hook_events: list[HookEvent] = []
        for matcher in self.stop:
            started = time.time()
            matched = True
            action: str | None = None
            if matcher.hook is not None:
                decision = await matcher.hook(
                    {"final_text": final_text, "context": dict(context), "hook_point": "Stop"}
                )
                action = decision.action
                if decision.block:
                    action = action or "block"
            hook_events.append(
                HookEvent(
                    hook_point="Stop",
                    name=matcher.name,
                    matched=matched,
                    duration_ms=(time.time() - started) * 1000,
                    action=action,
                )
            )
        return hook_events
