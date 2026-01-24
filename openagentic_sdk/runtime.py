from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Mapping, Sequence

from .events import (
    AssistantDelta,
    AssistantMessage,
    Result,
    SystemInit,
    ToolResult,
    ToolUse,
    UserMessage,
    UserQuestion,
)
from .hooks.engine import HookEngine
from .options import OpenAgenticOptions
from .providers.base import ModelOutput, ToolCall
from .project.claude import load_claude_project_settings
from .skills.index import index_skills
from .sessions.rebuild import rebuild_messages, rebuild_responses_input
from .sessions.store import FileSessionStore
from .tools.base import ToolContext
from .tools.openai import tool_schemas_for_openai
from .tools.openai_responses import tool_schemas_for_responses
from .mcp.sdk import McpSdkServerConfig, wrap_sdk_server_tools
from ._version import __version__ as _SDK_VERSION
from .paths import default_session_root


def _default_session_root() -> Path:
    return default_session_root()


def _build_project_system_prompt(options: OpenAgenticOptions) -> str | None:
    if "project" not in set(options.setting_sources):
        return None
    project_dir = options.project_dir or options.cwd
    settings = load_claude_project_settings(project_dir)

    parts: list[str] = []
    if settings.memory:
        parts.append(settings.memory.strip())
    if settings.commands:
        lines = ["## Slash Commands"]
        for c in settings.commands:
            lines.append(f"- /{c.name} ({c.path})")
        parts.append("\n".join(lines))
    out = "\n\n".join([p for p in parts if p]).strip()
    return out or None


_EXEC_SKILL_RE = re.compile(
    r"^\s*(?:执行技能|运行技能|run skill|execute skill)\s*[:：]?\s*([A-Za-z0-9_.-]+)\s*$",
    re.IGNORECASE,
)

_LIST_SKILLS_RE = re.compile(
    r"^\s*(?:what\s+skills\s+are\s+available\??|list\s+skills|有哪些技能\??|有什么技能\??|技能有哪些\??)\s*$",
    re.IGNORECASE,
)


def _maybe_expand_execute_skill_prompt(prompt: str, options: OpenAgenticOptions) -> str:
    """
    Best-effort helper for users who type "执行技能<name>" expecting an automatic skill run.

    If the prompt matches and the skill exists on disk, instruct the model to load it via the
    `Skill` tool and follow the Workflow/Checklist without asking for extra input.
    """
    m = _EXEC_SKILL_RE.match(prompt or "")
    if not m:
        return prompt

    skill_name = m.group(1)
    project_dir = options.project_dir or options.cwd
    skills = index_skills(project_dir=project_dir)
    match = next((s for s in skills if s.name == skill_name), None)
    if match is None:
        return prompt

    return (
        f"你正在执行技能 `{skill_name}`。\n"
        "除非技能文档明确要求，否则不要向用户询问额外的目标/输入。\n"
        "请严格按技能的 Workflow/Checklist 执行。\n\n"
        f'你 MUST 调用 `Skill` 工具加载该技能：`Skill({{"name": "{skill_name}"}})`。\n'
    )


def _maybe_expand_list_skills_prompt(prompt: str, options: OpenAgenticOptions) -> str:
    """
    Best-effort helper for users who ask to list available skills without explicitly naming the tool.
    """
    if not _LIST_SKILLS_RE.match(prompt or ""):
        return prompt

    # If there are no skills, keep the prompt as-is.
    project_dir = options.project_dir or options.cwd
    skills = index_skills(project_dir=project_dir)
    if not skills:
        return prompt

    return (
        "List the available Skills for this project.\n"
        "The available skills are listed in the `Skill` tool description under <available_skills>.\n"
        "Present them as a short bullet list: `name` — description (or summary).\n"
    )


def _unsupported_previous_response_id_error(e: BaseException) -> bool:
    msg = str(e)
    if not msg:
        return False
    msg_l = msg.lower()
    return "previous_response_id" in msg_l and ("unsupported parameter" in msg_l or "unsupported" in msg_l)


def _no_tool_call_found_for_call_output_error(e: BaseException) -> bool:
    msg = str(e)
    if not msg:
        return False
    msg_l = msg.lower()
    return "no tool call found for function call output" in msg_l and "call_id" in msg_l


def _looks_like_only_function_call_output(items: Sequence[Mapping[str, Any]]) -> bool:
    return bool(items) and all(isinstance(i, dict) and i.get("type") == "function_call_output" for i in items)


def _prepend_function_calls_for_responses(tool_calls: Sequence[ToolCall], outputs: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    calls: list[Mapping[str, Any]] = []
    for tc in tool_calls:
        calls.append(
            {
                "type": "function_call",
                "call_id": tc.tool_use_id,
                "name": tc.name,
                "arguments": json.dumps(tc.arguments, ensure_ascii=False),
            }
        )
    return calls + list(outputs)


@dataclass(frozen=True, slots=True)
class RunResult:
    final_text: str
    session_id: str
    events: Sequence[Any]


class AgentRuntime:
    def __init__(self, options: OpenAgenticOptions, *, agent_name: str | None = None, parent_tool_use_id: str | None = None):
        self._options = options
        self._agent_name = agent_name
        self._parent_tool_use_id = parent_tool_use_id

    async def query(self, prompt: str) -> AsyncIterator[Any]:
        options = self._options

        if options.mcp_servers:
            for server_key, cfg in options.mcp_servers.items():
                if isinstance(cfg, McpSdkServerConfig) and cfg.type == "sdk":
                    for wrapper in wrap_sdk_server_tools(server_key, cfg):
                        try:
                            options.tools.get(wrapper.name)
                        except KeyError:
                            options.tools.register(wrapper)

        store = options.session_store
        if store is None:
            root = options.session_root or _default_session_root()
            store = FileSessionStore(root_dir=root)

        previous_response_id: str | None = None
        supports_previous_response_id = True
        pending_responses_tool_calls: list[ToolCall] = []
        pending_responses_history: list[Mapping[str, Any]] = []
        resume_protocol: str | None = None
        if options.resume:
            session_id = options.resume
            past_events = store.read_events(session_id)
            for e in reversed(past_events):
                if isinstance(e, Result) and isinstance(getattr(e, "provider_metadata", None), dict):
                    pm = e.provider_metadata or {}
                    proto = pm.get("protocol")
                    if isinstance(proto, str) and proto:
                        resume_protocol = proto
                    spri = pm.get("supports_previous_response_id")
                    if isinstance(spri, bool):
                        supports_previous_response_id = spri
                    break
            for e in reversed(past_events):
                if isinstance(e, Result) and isinstance(getattr(e, "response_id", None), str) and e.response_id:
                    previous_response_id = e.response_id
                    break
            if resume_protocol == "responses" and supports_previous_response_id is False:
                messages = list(
                    rebuild_responses_input(
                        past_events,
                        max_events=options.resume_max_events,
                        max_bytes=options.resume_max_bytes,
                    )
                )
            else:
                messages = list(
                    rebuild_messages(
                        past_events,
                        max_events=options.resume_max_events,
                        max_bytes=options.resume_max_bytes,
                    )
                )
        else:
            metadata: dict[str, Any] = {
                "cwd": options.cwd,
                "provider_name": getattr(options.provider, "name", "unknown"),
                "model": options.model,
            }
            if options.setting_sources:
                metadata["setting_sources"] = list(options.setting_sources)
            if options.allowed_tools is not None:
                metadata["allowed_tools"] = list(options.allowed_tools)
            session_id = store.create_session(metadata=metadata)
            messages = []

        init = SystemInit(
            session_id=session_id,
            cwd=options.cwd,
            sdk_version=_SDK_VERSION,
            parent_tool_use_id=self._parent_tool_use_id,
            agent_name=self._agent_name,
            enabled_tools=options.tools.names(),
            enabled_providers=[getattr(options.provider, "name", "unknown")],
        )
        store.append_event(session_id, init)
        yield init

        for he in await options.hooks.run_session_start(context={"session_id": session_id, "agent_name": self._agent_name}):
            store.append_event(session_id, he)
            yield he

        sys_prompt = _build_project_system_prompt(options)
        if sys_prompt:
            messages.insert(0, {"role": "system", "content": sys_prompt})
        self._base_system_prompt = sys_prompt

        prompt2, hook_events0, decision0 = await options.hooks.run_user_prompt_submit(
            prompt=prompt,
            context={"session_id": session_id, "agent_name": self._agent_name},
        )
        for he in hook_events0:
            store.append_event(session_id, he)
            yield he
        if decision0 is not None and decision0.block:
            for he in await options.hooks.run_session_end(context={"session_id": session_id, "agent_name": self._agent_name}):
                store.append_event(session_id, he)
                yield he
            final = Result(
                final_text="",
                session_id=session_id,
                stop_reason=f"blocked:user_prompt_submit:{decision0.block_reason or 'blocked'}",
                steps=0,
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            )
            store.append_event(session_id, final)
            yield final
            return

        prompt3 = _maybe_expand_execute_skill_prompt(prompt2, options)
        prompt3 = _maybe_expand_list_skills_prompt(prompt3, options)

        store.append_event(
            session_id,
            UserMessage(
                text=prompt3,
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            ),
        )

        messages.append({"role": "user", "content": prompt3})
        provider_protocol: str | None = None  # "responses" | "legacy"
        steps = 0
        while steps < options.max_steps:
            if options.abort_event is not None and getattr(options.abort_event, "is_set", lambda: False)():
                for he in await options.hooks.run_session_end(
                    context={"session_id": session_id, "agent_name": self._agent_name}
                ):
                    store.append_event(session_id, he)
                    yield he
                final = Result(
                    final_text="",
                    session_id=session_id,
                    stop_reason="interrupted",
                    steps=steps,
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
                store.append_event(session_id, final)
                yield final
                return
            steps += 1
            tool_names = options.tools.names()
            if options.agents:
                tool_names = [*tool_names, "Task"]
            if options.allowed_tools is not None:
                allowed = set(options.allowed_tools)
                tool_names = [t for t in tool_names if t in allowed]

            tool_schemas: Sequence[Mapping[str, Any]] = ()
            if provider_protocol == "legacy":
                tool_schemas = tool_schemas_for_openai(
                    tool_names,
                    registry=options.tools,
                    context={"cwd": options.cwd, "project_dir": options.project_dir},
                )
            else:
                tool_schemas = tool_schemas_for_responses(
                    tool_names,
                    registry=options.tools,
                    context={"cwd": options.cwd, "project_dir": options.project_dir},
                )

            if getattr(self, "_base_system_prompt", None) and messages and messages[0].get("role") == "system":
                messages[0] = {
                    "role": "system",
                    "content": self._base_system_prompt,  # type: ignore[arg-type]
                }

            model_ctx = {
                "session_id": session_id,
                "model": options.model,
                "provider_name": getattr(options.provider, "name", "unknown"),
                "agent_name": self._agent_name,
            }
            messages2, hook_events, decision = await options.hooks.run_before_model_call(
                messages=messages, context=model_ctx
            )
            for he in hook_events:
                store.append_event(session_id, he)
                yield he
            if decision is not None and decision.block:
                for he in await options.hooks.run_session_end(context=model_ctx):
                    store.append_event(session_id, he)
                    yield he
                final = Result(
                    final_text="",
                    session_id=session_id,
                    stop_reason=f"blocked:before_model_call:{decision.block_reason or 'blocked'}",
                    steps=steps,
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
                store.append_event(session_id, final)
                yield final
                return
            messages = list(messages2)

            model_out: ModelOutput
            if hasattr(options.provider, "stream"):
                stream_fn = getattr(options.provider, "stream")
                interrupted = False
                parts: list[str] = []
                tool_calls: list[ToolCall] = []
                stream_response_id: str | None = None
                stream_usage: Mapping[str, Any] | None = None

                for attempt in range(2):
                    parts = []
                    tool_calls = []
                    stream_response_id = None
                    stream_usage = None

                    if provider_protocol == "legacy":
                        stream_iter = stream_fn(
                            model=options.model, messages=messages, tools=tool_schemas, api_key=options.api_key
                        )
                    else:
                        prev_id = previous_response_id if supports_previous_response_id else None
                        try:
                            stream_iter = stream_fn(
                                model=options.model,
                                input=messages,
                                tools=tool_schemas,
                                api_key=options.api_key,
                                previous_response_id=prev_id,
                                store=True,
                            )
                            if provider_protocol is None:
                                provider_protocol = "responses"
                        except TypeError as e:
                            if provider_protocol is None and "unexpected keyword argument" in str(e):
                                provider_protocol = "legacy"
                                tool_schemas = tool_schemas_for_openai(
                                    tool_names,
                                    registry=options.tools,
                                    context={"cwd": options.cwd, "project_dir": options.project_dir},
                                )
                                stream_iter = stream_fn(
                                    model=options.model, messages=messages, tools=tool_schemas, api_key=options.api_key
                                )
                            else:
                                raise

                    try:
                        async for ev in stream_iter:
                            if options.abort_event is not None and getattr(options.abort_event, "is_set", lambda: False)():
                                interrupted = True
                                break
                            ev_type = getattr(ev, "type", None)
                            if ev_type is None and isinstance(ev, dict):
                                ev_type = ev.get("type")
                            if ev_type == "text_delta":
                                delta = getattr(ev, "delta", None)
                                if delta is None and isinstance(ev, dict):
                                    delta = ev.get("delta")
                                if isinstance(delta, str) and delta:
                                    parts.append(delta)
                                    de = AssistantDelta(
                                        text_delta=delta,
                                        parent_tool_use_id=self._parent_tool_use_id,
                                        agent_name=self._agent_name,
                                    )
                                    store.append_event(session_id, de)
                                    yield de
                            elif ev_type == "tool_call":
                                tc = getattr(ev, "tool_call", None)
                                if tc is None and isinstance(ev, dict):
                                    tc = ev.get("tool_call")
                                if isinstance(tc, ToolCall):
                                    tool_calls.append(tc)
                            elif ev_type == "done":
                                rid = getattr(ev, "response_id", None)
                                if rid is None and isinstance(ev, dict):
                                    rid = ev.get("response_id")
                                if isinstance(rid, str) and rid:
                                    stream_response_id = rid

                                u = getattr(ev, "usage", None)
                                if u is None and isinstance(ev, dict):
                                    u = ev.get("usage")
                                if isinstance(u, dict):
                                    stream_usage = u
                                break
                    except RuntimeError as e:
                        can_retry_prev = (
                            supports_previous_response_id
                            and previous_response_id is not None
                            and _unsupported_previous_response_id_error(e)
                        )
                        can_retry_link = supports_previous_response_id and _no_tool_call_found_for_call_output_error(e)
                        can_retry = (
                            provider_protocol != "legacy"
                            and attempt == 0
                            and supports_previous_response_id
                            and not parts
                            and not tool_calls
                            and stream_response_id is None
                            and (can_retry_prev or can_retry_link)
                        )
                        if can_retry:
                            supports_previous_response_id = False
                            if (
                                pending_responses_tool_calls
                                and pending_responses_history
                                and _looks_like_only_function_call_output(messages)
                            ):
                                messages = [
                                    *list(pending_responses_history),
                                    *_prepend_function_calls_for_responses(pending_responses_tool_calls, messages),
                                ]
                            continue
                        raise
                    break
                if interrupted:
                    for he in await options.hooks.run_session_end(context=model_ctx):
                        store.append_event(session_id, he)
                        yield he
                    final = Result(
                        final_text="",
                        session_id=session_id,
                        stop_reason="interrupted",
                        steps=steps,
                        parent_tool_use_id=self._parent_tool_use_id,
                        agent_name=self._agent_name,
                    )
                    store.append_event(session_id, final)
                    yield final
                    return
                assistant_text = "".join(parts) if parts else None
                model_out = ModelOutput(
                    assistant_text=assistant_text,
                    tool_calls=tool_calls,
                    usage=stream_usage,
                    response_id=stream_response_id,
                )
            else:
                if provider_protocol == "legacy":
                    model_out = await options.provider.complete(
                        model=options.model,
                        messages=messages,
                        tools=tool_schemas,
                        api_key=options.api_key,
                    )
                else:
                    prev_id = previous_response_id if supports_previous_response_id else None
                    try:
                        model_out = await options.provider.complete(
                            model=options.model,
                            input=messages,
                            tools=tool_schemas,
                            api_key=options.api_key,
                            previous_response_id=prev_id,
                            store=True,
                        )
                        if provider_protocol is None:
                            provider_protocol = "responses"
                    except RuntimeError as e:
                        can_retry_prev = (
                            supports_previous_response_id
                            and previous_response_id is not None
                            and _unsupported_previous_response_id_error(e)
                        )
                        can_retry_link = supports_previous_response_id and _no_tool_call_found_for_call_output_error(e)
                        can_retry = can_retry_prev or can_retry_link
                        if can_retry:
                            supports_previous_response_id = False
                            if (
                                pending_responses_tool_calls
                                and pending_responses_history
                                and _looks_like_only_function_call_output(messages)
                            ):
                                messages = [
                                    *list(pending_responses_history),
                                    *_prepend_function_calls_for_responses(pending_responses_tool_calls, messages),
                                ]
                            model_out = await options.provider.complete(
                                model=options.model,
                                input=messages,
                                tools=tool_schemas,
                                api_key=options.api_key,
                                previous_response_id=None,
                                store=True,
                            )
                            if provider_protocol is None:
                                provider_protocol = "responses"
                        else:
                            raise
                    except TypeError as e:
                        if provider_protocol is None and "unexpected keyword argument" in str(e):
                            provider_protocol = "legacy"
                            tool_schemas = tool_schemas_for_openai(
                                tool_names,
                                registry=options.tools,
                                context={"cwd": options.cwd, "project_dir": options.project_dir},
                            )
                            model_out = await options.provider.complete(
                                model=options.model,
                                messages=messages,
                                tools=tool_schemas,
                                api_key=options.api_key,
                            )
                        else:
                            raise
            model_out2, hook_events2, decision2 = await options.hooks.run_after_model_call(
                output=model_out, context=model_ctx
            )
            for he in hook_events2:
                store.append_event(session_id, he)
                yield he
            if decision2 is not None and decision2.block:
                for he in await options.hooks.run_session_end(context=model_ctx):
                    store.append_event(session_id, he)
                    yield he
                final = Result(
                    final_text="",
                    session_id=session_id,
                    stop_reason=f"blocked:after_model_call:{decision2.block_reason or 'blocked'}",
                    steps=steps,
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
                store.append_event(session_id, final)
                yield final
                return
            model_out = model_out2

            if model_out.tool_calls:
                tool_calls = list(model_out.tool_calls)
                pending_responses_tool_calls = tool_calls
                if provider_protocol == "legacy":
                    # Record assistant tool-call message in OpenAI chat-completions format so tool results can link.
                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tc.tool_use_id,
                                    "type": "function",
                                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                                }
                                for tc in tool_calls
                            ],
                        }
                    )
                    for tc in tool_calls:
                        async for e in self._run_tool_call(session_id=session_id, tool_call=tc, store=store, hooks=options.hooks):
                            yield e
                            if isinstance(e, ToolResult):
                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tc.tool_use_id,
                                        "content": json.dumps(e.output, ensure_ascii=False),
                                    }
                                )
                    continue

                if supports_previous_response_id:
                    tool_output_items: list[Mapping[str, Any]] = []
                    for tc in tool_calls:
                        async for e in self._run_tool_call(session_id=session_id, tool_call=tc, store=store, hooks=options.hooks):
                            yield e
                            if isinstance(e, ToolResult):
                                tool_output_items.append(
                                    {
                                        "type": "function_call_output",
                                        "call_id": tc.tool_use_id,
                                        "output": json.dumps(e.output, ensure_ascii=False),
                                    }
                                )
                    if model_out.response_id:
                        previous_response_id = model_out.response_id
                    pending_responses_history = list(messages)
                    messages = tool_output_items
                    continue

                for tc in tool_calls:
                    messages.append(
                        {
                            "type": "function_call",
                            "call_id": tc.tool_use_id,
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        }
                    )
                    async for e in self._run_tool_call(session_id=session_id, tool_call=tc, store=store, hooks=options.hooks):
                        yield e
                        if isinstance(e, ToolResult):
                            messages.append(
                                {
                                    "type": "function_call_output",
                                    "call_id": tc.tool_use_id,
                                    "output": json.dumps(e.output, ensure_ascii=False),
                                }
                            )
                continue

            if model_out.assistant_text is None:
                for he in await options.hooks.run_session_end(context=model_ctx):
                    store.append_event(session_id, he)
                    yield he
                final = Result(
                    final_text="",
                    session_id=session_id,
                    stop_reason="no_output",
                    steps=steps,
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
                store.append_event(session_id, final)
                yield final
                return

            msg = AssistantMessage(
                text=model_out.assistant_text,
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            )
            store.append_event(session_id, msg)
            yield msg

            for he in await options.hooks.run_stop(final_text=model_out.assistant_text, context=model_ctx):
                store.append_event(session_id, he)
                yield he

            for he in await options.hooks.run_session_end(context=model_ctx):
                store.append_event(session_id, he)
                yield he

            final = Result(
                final_text=model_out.assistant_text,
                session_id=session_id,
                stop_reason="end",
                usage=model_out.usage if isinstance(model_out.usage, dict) else None,
                response_id=model_out.response_id or previous_response_id,
                provider_metadata={
                    **({"protocol": provider_protocol} if provider_protocol else {}),
                    **(
                        {"supports_previous_response_id": supports_previous_response_id}
                        if provider_protocol == "responses"
                        else {}
                    ),
                    **(dict(model_out.provider_metadata) if isinstance(model_out.provider_metadata, dict) else {}),
                }
                or None,
                steps=steps,
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            )
            store.append_event(session_id, final)
            yield final
            return

        final = Result(
            final_text="",
            session_id=session_id,
            stop_reason="max_steps",
            steps=steps,
            parent_tool_use_id=self._parent_tool_use_id,
            agent_name=self._agent_name,
        )
        for he in await options.hooks.run_session_end(context={"session_id": session_id, "agent_name": self._agent_name}):
            store.append_event(session_id, he)
            yield he
        store.append_event(session_id, final)
        yield final

    async def _run_tool_call(
        self,
        *,
        session_id: str,
        tool_call: ToolCall,
        store: FileSessionStore,
        hooks: HookEngine,
    ) -> AsyncIterator[Any]:
        options = self._options
        tool_name = tool_call.name
        tool_input: Mapping[str, Any] = tool_call.arguments

        allowed_tools = options.allowed_tools
        if allowed_tools is not None and tool_name not in set(allowed_tools):
            denied = ToolResult(
                tool_use_id=tool_call.tool_use_id,
                output=None,
                is_error=True,
                error_type="ToolNotAllowed",
                error_message=f"Tool '{tool_name}' is not allowed",
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            )
            store.append_event(session_id, denied)
            yield denied
            return

        use_event = ToolUse(
            tool_use_id=tool_call.tool_use_id,
            name=tool_name,
            input=tool_input,
            parent_tool_use_id=self._parent_tool_use_id,
            agent_name=self._agent_name,
        )
        store.append_event(session_id, use_event)
        yield use_event

        ctx = {"session_id": session_id, "tool_use_id": tool_call.tool_use_id, "agent_name": self._agent_name}
        tool_input2, hook_events, decision = await hooks.run_pre_tool_use(
            tool_name=tool_name,
            tool_input=tool_input,
            context=ctx,
        )
        for he in hook_events:
            store.append_event(session_id, he)
            yield he
        if decision is not None and decision.block:
            blocked = ToolResult(
                tool_use_id=tool_call.tool_use_id,
                output=None,
                is_error=True,
                error_type="HookBlocked",
                error_message=decision.block_reason or "blocked by hook",
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            )
            store.append_event(session_id, blocked)
            yield blocked
            return

        approval = await options.permission_gate.approve(tool_name, tool_input2, context=ctx)
        if approval.question is not None:
            store.append_event(session_id, approval.question)
            yield approval.question
        if not approval.allowed:
            denied = ToolResult(
                tool_use_id=tool_call.tool_use_id,
                output=None,
                is_error=True,
                error_type="PermissionDenied",
                error_message=approval.deny_message or "tool use not approved",
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            )
            store.append_event(session_id, denied)
            yield denied
            return
        tool_input2 = approval.updated_input or tool_input2

        if tool_name == "AskUserQuestion":
            questions = tool_input2.get("questions")
            if isinstance(questions, dict):
                questions = [questions]

            if not isinstance(questions, list) or not questions:
                q_text0 = tool_input2.get("question", tool_input2.get("prompt"))
                if isinstance(q_text0, str) and q_text0.strip():
                    opts0 = tool_input2.get("options", tool_input2.get("choices")) or []
                    options0: list[dict[str, str]] = []
                    if isinstance(opts0, list):
                        for opt in opts0:
                            if isinstance(opt, str) and opt.strip():
                                options0.append({"label": opt.strip()})
                                continue
                            if isinstance(opt, dict):
                                lab = opt.get("label", opt.get("name", opt.get("value")))
                                if isinstance(lab, str) and lab.strip():
                                    options0.append({"label": lab.strip()})
                    questions = [{"question": q_text0.strip(), "options": options0}]

            if not isinstance(questions, list) or not questions:
                result = ToolResult(
                    tool_use_id=tool_call.tool_use_id,
                    output=None,
                    is_error=True,
                    error_type="InvalidAskUserQuestionInput",
                    error_message="AskUserQuestion: 'questions' must be a non-empty list",
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
                store.append_event(session_id, result)
                yield result
                return

            user_answerer = options.permission_gate.user_answerer
            if user_answerer is None:
                result = ToolResult(
                    tool_use_id=tool_call.tool_use_id,
                    output=None,
                    is_error=True,
                    error_type="NoUserAnswerer",
                    error_message="AskUserQuestion: no user_answerer is configured",
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
                store.append_event(session_id, result)
                yield result
                return

            answers: dict[str, str] = {}
            for i, q in enumerate(questions):
                if not isinstance(q, dict):
                    continue
                q_text = q.get("question")
                if not isinstance(q_text, str) or not q_text:
                    continue
                opts = q.get("options") or []
                labels: list[str] = []
                if isinstance(opts, list):
                    for opt in opts:
                        if isinstance(opt, dict):
                            lab = opt.get("label")
                            if isinstance(lab, str) and lab:
                                labels.append(lab)
                if not labels:
                    labels = ["ok"]

                uq = UserQuestion(
                    question_id=f"{tool_call.tool_use_id}:{i}",
                    prompt=q_text,
                    choices=labels,
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
                store.append_event(session_id, uq)
                yield uq
                ans = await user_answerer(uq)
                answers[q_text] = str(ans)

            result = ToolResult(
                tool_use_id=tool_call.tool_use_id,
                output={"questions": questions, "answers": answers},
                is_error=False,
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            )
            store.append_event(session_id, result)
            yield result
            return

        if tool_name == "Task":
            agent = tool_input2.get("agent")
            task_prompt = tool_input2.get("prompt")
            if not isinstance(agent, str) or not agent:
                result = ToolResult(
                    tool_use_id=tool_call.tool_use_id,
                    output=None,
                    is_error=True,
                    error_type="InvalidTaskInput",
                    error_message="Task: 'agent' must be a non-empty string",
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
                store.append_event(session_id, result)
                yield result
                return
            if not isinstance(task_prompt, str) or not task_prompt:
                result = ToolResult(
                    tool_use_id=tool_call.tool_use_id,
                    output=None,
                    is_error=True,
                    error_type="InvalidTaskInput",
                    error_message="Task: 'prompt' must be a non-empty string",
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
                store.append_event(session_id, result)
                yield result
                return

            definition = options.agents.get(agent)
            if definition is None:
                result = ToolResult(
                    tool_use_id=tool_call.tool_use_id,
                    output=None,
                    is_error=True,
                    error_type="UnknownAgent",
                    error_message=f"Unknown agent '{agent}'",
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
                store.append_event(session_id, result)
                yield result
                return

            child_session_id = store.create_session(
                metadata={
                    "parent_session_id": session_id,
                    "parent_tool_use_id": tool_call.tool_use_id,
                    "agent_name": agent,
                }
            )
            child_options = OpenAgenticOptions(
                provider=definition.provider or options.provider,
                model=definition.model or options.model,
                api_key=options.api_key,
                cwd=options.cwd,
                max_steps=options.max_steps,
                timeout_s=options.timeout_s,
                tools=options.tools,
                allowed_tools=list(definition.tools) if definition.tools else options.allowed_tools,
                permission_gate=options.permission_gate,
                hooks=options.hooks,
                session_store=store,
                resume=child_session_id,
                setting_sources=options.setting_sources,
                agents=options.agents,
            )

            child_runtime = AgentRuntime(child_options, agent_name=agent, parent_tool_use_id=tool_call.tool_use_id)
            combined_prompt = definition.prompt + "\n\n" + task_prompt
            child_final_text = ""
            async for child_event in child_runtime.query(combined_prompt):
                store.append_event(session_id, child_event)
                yield child_event
                if isinstance(child_event, Result):
                    child_final_text = child_event.final_text

            result = ToolResult(
                tool_use_id=tool_call.tool_use_id,
                output={"child_session_id": child_session_id, "final_text": child_final_text},
                is_error=False,
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            )
            store.append_event(session_id, result)
            yield result
            return

        if tool_name == "WebFetch":
            prompt_text = tool_input2.get("prompt")
            if isinstance(prompt_text, str) and prompt_text:
                try:
                    tool = options.tools.get(tool_name)
                    fetched = await tool.run(tool_input2, ToolContext(cwd=options.cwd, project_dir=options.project_dir))
                    page_text = fetched.get("text", "") if isinstance(fetched, dict) else ""
                    if not isinstance(page_text, str):
                        page_text = str(page_text)
                    model_out = await options.provider.complete(
                        model=options.model,
                        messages=[
                            {
                                "role": "user",
                                "content": f"{prompt_text}\n\nCONTENT:\n{page_text}",
                            }
                        ],
                        tools=(),
                        api_key=options.api_key,
                    )
                    response = model_out.assistant_text or ""
                    output: dict[str, Any] = {
                        "response": response,
                        "url": fetched.get("url") if isinstance(fetched, dict) else tool_input2.get("url"),
                        "final_url": fetched.get("url") if isinstance(fetched, dict) else None,
                        "status_code": fetched.get("status") if isinstance(fetched, dict) else None,
                    }
                    output2, post_events, post_decision = await hooks.run_post_tool_use(
                        tool_name=tool_name,
                        tool_output=output,
                        context=ctx,
                    )
                    for he in post_events:
                        store.append_event(session_id, he)
                        yield he
                    if post_decision is not None and post_decision.block:
                        raise RuntimeError(post_decision.block_reason or "blocked by hook")
                    result = ToolResult(
                        tool_use_id=tool_call.tool_use_id,
                        output=output2,
                        is_error=False,
                        parent_tool_use_id=self._parent_tool_use_id,
                        agent_name=self._agent_name,
                    )
                except Exception as e:  # noqa: BLE001
                    result = ToolResult(
                        tool_use_id=tool_call.tool_use_id,
                        output=None,
                        is_error=True,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        parent_tool_use_id=self._parent_tool_use_id,
                        agent_name=self._agent_name,
                    )
                store.append_event(session_id, result)
                yield result
                return

        if tool_name == "TodoWrite":
            try:
                tool = options.tools.get(tool_name)
                output = await tool.run(tool_input2, ToolContext(cwd=options.cwd, project_dir=options.project_dir))
                todos = tool_input2.get("todos")
                if isinstance(todos, list):
                    p = store.session_dir(session_id) / "todos.json"
                    p.write_text(json.dumps({"todos": todos}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

                output2, post_events, post_decision = await hooks.run_post_tool_use(
                    tool_name=tool_name,
                    tool_output=output,
                    context=ctx,
                )
                for he in post_events:
                    store.append_event(session_id, he)
                    yield he
                if post_decision is not None and post_decision.block:
                    raise RuntimeError(post_decision.block_reason or "blocked by hook")
                result = ToolResult(
                    tool_use_id=tool_call.tool_use_id,
                    output=output2,
                    is_error=False,
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
            except Exception as e:  # noqa: BLE001
                result = ToolResult(
                    tool_use_id=tool_call.tool_use_id,
                    output=None,
                    is_error=True,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
            store.append_event(session_id, result)
            yield result
            return

        try:
            tool = options.tools.get(tool_name)
            output = await tool.run(tool_input2, ToolContext(cwd=options.cwd, project_dir=options.project_dir))
            output2, post_events, post_decision = await hooks.run_post_tool_use(
                tool_name=tool_name,
                tool_output=output,
                context=ctx,
            )
            for he in post_events:
                store.append_event(session_id, he)
                yield he
            if post_decision is not None and post_decision.block:
                raise RuntimeError(post_decision.block_reason or "blocked by hook")
            output = output2
            result = ToolResult(
                tool_use_id=tool_call.tool_use_id,
                output=output,
                is_error=False,
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            )
        except Exception as e:  # noqa: BLE001
            result = ToolResult(
                tool_use_id=tool_call.tool_use_id,
                output=None,
                is_error=True,
                error_type=type(e).__name__,
                error_message=str(e),
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            )

        store.append_event(session_id, result)
        yield result
