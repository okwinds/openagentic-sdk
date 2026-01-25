from __future__ import annotations

import asyncio
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
    user_prompt_submit: Sequence[HookMatcher] = ()
    before_model_call: Sequence[HookMatcher] = ()
    after_model_call: Sequence[HookMatcher] = ()
    session_start: Sequence[HookMatcher] = ()
    session_end: Sequence[HookMatcher] = ()
    # OpenCode parity: plugins can influence compaction prompt/context.
    session_compacting: Sequence[HookMatcher] = ()
    stop: Sequence[HookMatcher] = ()
    enable_message_rewrite_hooks: bool = False

    async def run_session_compacting(
        self, *, output: Any, context: Mapping[str, Any]
    ) -> tuple[Any, list[HookEvent], HookDecision | None]:
        current_output: Any = output
        hook_events: list[HookEvent] = []
        for matcher in self.session_compacting:
            matched = _match_name(matcher.tool_name_pattern, "SessionCompacting")
            started = time.time()
            decision: HookDecision | None = None
            action: str | None = None
            callbacks = [*([matcher.hook] if matcher.hook is not None else []), *list(matcher.hooks)]
            if matched and callbacks:
                for cb in callbacks:
                    payload = {
                        "output": current_output,
                        "context": dict(context),
                        "hook_point": "SessionCompacting",
                    }
                    if matcher.timeout_s is not None:
                        decision = await asyncio.wait_for(cb(payload), timeout=float(matcher.timeout_s))
                    else:
                        decision = await cb(payload)
                    action = decision.action or action
                    if decision.block:
                        hook_events.append(
                            HookEvent(
                                hook_point="SessionCompacting",
                                name=matcher.name,
                                matched=True,
                                duration_ms=(time.time() - started) * 1000,
                                action=action or "block",
                            )
                        )
                        return current_output, hook_events, decision
                    if decision.override_tool_output is not None:
                        current_output = decision.override_tool_output
                        action = action or "rewrite_compaction"
            hook_events.append(
                HookEvent(
                    hook_point="SessionCompacting",
                    name=matcher.name,
                    matched=matched,
                    duration_ms=(time.time() - started) * 1000,
                    action=action,
                )
            )
        return current_output, hook_events, None

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
            callbacks = [*([matcher.hook] if matcher.hook is not None else []), *list(matcher.hooks)]
            if matched and callbacks:
                for cb in callbacks:
                    payload = {
                        "tool_name": tool_name,
                        "tool_input": dict(current_input),
                        "context": dict(context),
                        "hook_point": "PreToolUse",
                    }
                    if matcher.timeout_s is not None:
                        decision = await asyncio.wait_for(cb(payload), timeout=float(matcher.timeout_s))
                    else:
                        decision = await cb(payload)
                    action = decision.action or action
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
            callbacks = [*([matcher.hook] if matcher.hook is not None else []), *list(matcher.hooks)]
            if matched and callbacks:
                for cb in callbacks:
                    payload = {
                        "tool_name": tool_name,
                        "tool_output": current_output,
                        "context": dict(context),
                        "hook_point": "PostToolUse",
                    }
                    if matcher.timeout_s is not None:
                        decision = await asyncio.wait_for(cb(payload), timeout=float(matcher.timeout_s))
                    else:
                        decision = await cb(payload)
                    action = decision.action or action
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

    async def run_user_prompt_submit(
        self, *, prompt: str, context: Mapping[str, Any]
    ) -> tuple[str, list[HookEvent], HookDecision | None]:
        current_prompt = prompt
        hook_events: list[HookEvent] = []
        for matcher in self.user_prompt_submit:
            matched = _match_name(matcher.tool_name_pattern, "UserPromptSubmit")
            started = time.time()
            decision: HookDecision | None = None
            action: str | None = None
            callbacks = [*([matcher.hook] if matcher.hook is not None else []), *list(matcher.hooks)]
            if matched and callbacks:
                for cb in callbacks:
                    payload = {"prompt": current_prompt, "context": dict(context), "hook_point": "UserPromptSubmit"}
                    if matcher.timeout_s is not None:
                        decision = await asyncio.wait_for(cb(payload), timeout=float(matcher.timeout_s))
                    else:
                        decision = await cb(payload)
                    action = decision.action or action
                    if decision.block:
                        hook_events.append(
                            HookEvent(
                                hook_point="UserPromptSubmit",
                                name=matcher.name,
                                matched=True,
                                duration_ms=(time.time() - started) * 1000,
                                action=action or "block",
                            )
                        )
                        return current_prompt, hook_events, decision
                    if decision.override_prompt is not None:
                        current_prompt = decision.override_prompt
                        action = action or "rewrite_prompt"
            hook_events.append(
                HookEvent(
                    hook_point="UserPromptSubmit",
                    name=matcher.name,
                    matched=matched,
                    duration_ms=(time.time() - started) * 1000,
                    action=action,
                )
            )
        return current_prompt, hook_events, None

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
            callbacks = [*([matcher.hook] if matcher.hook is not None else []), *list(matcher.hooks)]
            if matched and callbacks:
                for cb in callbacks:
                    payload = {
                        "messages": list(current_messages),
                        "context": dict(context),
                        "hook_point": "BeforeModelCall",
                    }
                    if matcher.timeout_s is not None:
                        decision = await asyncio.wait_for(cb(payload), timeout=float(matcher.timeout_s))
                    else:
                        decision = await cb(payload)
                    action = decision.action or action
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
            callbacks = [*([matcher.hook] if matcher.hook is not None else []), *list(matcher.hooks)]
            if matched and callbacks:
                for cb in callbacks:
                    payload = {"output": current_output, "context": dict(context), "hook_point": "AfterModelCall"}
                    if matcher.timeout_s is not None:
                        decision = await asyncio.wait_for(cb(payload), timeout=float(matcher.timeout_s))
                    else:
                        decision = await cb(payload)
                    action = decision.action or action
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
            callbacks = [*([matcher.hook] if matcher.hook is not None else []), *list(matcher.hooks)]
            if callbacks:
                for cb in callbacks:
                    payload = {"context": dict(context), "hook_point": "SessionStart"}
                    if matcher.timeout_s is not None:
                        decision = await asyncio.wait_for(cb(payload), timeout=float(matcher.timeout_s))
                    else:
                        decision = await cb(payload)
                    action = decision.action or action
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
            callbacks = [*([matcher.hook] if matcher.hook is not None else []), *list(matcher.hooks)]
            if callbacks:
                for cb in callbacks:
                    payload = {"context": dict(context), "hook_point": "SessionEnd"}
                    if matcher.timeout_s is not None:
                        decision = await asyncio.wait_for(cb(payload), timeout=float(matcher.timeout_s))
                    else:
                        decision = await cb(payload)
                    action = decision.action or action
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
            callbacks = [*([matcher.hook] if matcher.hook is not None else []), *list(matcher.hooks)]
            if callbacks:
                for cb in callbacks:
                    payload = {"final_text": final_text, "context": dict(context), "hook_point": "Stop"}
                    if matcher.timeout_s is not None:
                        decision = await asyncio.wait_for(cb(payload), timeout=float(matcher.timeout_s))
                    else:
                        decision = await cb(payload)
                    action = decision.action or action
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
