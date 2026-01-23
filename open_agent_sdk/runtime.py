from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Mapping, Sequence

from .events import (
    AssistantDelta,
    AssistantMessage,
    Result,
    SkillActivated,
    SystemInit,
    ToolResult,
    ToolUse,
    UserMessage,
    UserQuestion,
)
from .hooks.engine import HookEngine
from .options import OpenAgentOptions
from .providers.base import ModelOutput, ToolCall
from .project.claude import load_claude_project_settings
from .skills.index import index_skills
from .sessions.rebuild import rebuild_messages
from .sessions.store import FileSessionStore
from .tools.base import ToolContext
from .tools.openai import tool_schemas_for_openai
from .mcp.sdk import McpSdkServerConfig, wrap_sdk_server_tools


def _default_session_root() -> Path:
    env = os.environ.get("OPEN_AGENT_SDK_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".open-agent-sdk"


def _build_project_system_prompt(options: OpenAgentOptions) -> str | None:
    if "project" not in set(options.setting_sources):
        return None
    project_dir = options.project_dir or options.cwd
    settings = load_claude_project_settings(project_dir)
    skills = index_skills(project_dir=project_dir)

    parts: list[str] = []
    if settings.memory:
        parts.append(settings.memory.strip())
    if skills:
        lines = ["## Skills", "Use `SkillList`/`SkillLoad` to inspect skills at runtime."]
        for s in skills:
            summary = f": {s.summary}" if s.summary else ""
            lines.append(f"- {s.name}{summary} ({s.path})")
        parts.append("\n".join(lines))
    if settings.commands:
        lines = ["## Slash Commands"]
        for c in settings.commands:
            lines.append(f"- /{c.name} ({c.path})")
        parts.append("\n".join(lines))
    out = "\n\n".join([p for p in parts if p]).strip()
    return out or None


def _render_system_prompt(base: str, active_skills: list[str]) -> str:
    if not active_skills:
        return base
    lines = [base, "## Active Skills", *[f"- {n}" for n in active_skills]]
    return "\n\n".join([ln for ln in lines if ln]).strip()


def _rebuild_active_skills(events: Sequence[Any]) -> list[str]:
    active: list[str] = []
    for e in events:
        if isinstance(e, SkillActivated) and e.name and e.name not in active:
            active.append(e.name)
    return active


@dataclass(frozen=True, slots=True)
class RunResult:
    final_text: str
    session_id: str
    events: Sequence[Any]


class AgentRuntime:
    def __init__(self, options: OpenAgentOptions, *, agent_name: str | None = None, parent_tool_use_id: str | None = None):
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

        if options.resume:
            session_id = options.resume
            past_events = store.read_events(session_id)
            messages: list[Mapping[str, Any]] = list(
                rebuild_messages(
                    past_events,
                    max_events=options.resume_max_events,
                    max_bytes=options.resume_max_bytes,
                )
            )
            self._active_skills = _rebuild_active_skills(past_events)
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
            self._active_skills = []

        init = SystemInit(
            session_id=session_id,
            cwd=options.cwd,
            sdk_version="0.0.0",
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
            messages.insert(0, {"role": "system", "content": _render_system_prompt(sys_prompt, self._active_skills)})
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

        store.append_event(
            session_id,
            UserMessage(
                text=prompt2,
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            ),
        )

        messages.append({"role": "user", "content": prompt2})
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
            if getattr(options.provider, "name", None) in ("openai", "openai-compatible"):
                tool_schemas = tool_schemas_for_openai(tool_names, registry=options.tools)

            if getattr(self, "_base_system_prompt", None) and messages and messages[0].get("role") == "system":
                messages[0] = {
                    "role": "system",
                    "content": _render_system_prompt(self._base_system_prompt, self._active_skills),  # type: ignore[arg-type]
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
                parts: list[str] = []
                tool_calls: list[ToolCall] = []
                stream_fn = getattr(options.provider, "stream")
                interrupted = False
                async for ev in stream_fn(model=options.model, messages=messages, tools=tool_schemas, api_key=options.api_key):
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
                model_out = ModelOutput(assistant_text=assistant_text, tool_calls=tool_calls)
            else:
                model_out = await options.provider.complete(
                    model=options.model,
                    messages=messages,
                    tools=tool_schemas,
                    api_key=options.api_key,
                )
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
                # Record assistant tool-call message in provider-native format
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

        if tool_name == "SkillActivate":
            skill_name = tool_input2.get("name")
            if not isinstance(skill_name, str) or not skill_name:
                result = ToolResult(
                    tool_use_id=tool_call.tool_use_id,
                    output=None,
                    is_error=True,
                    error_type="InvalidSkillActivateInput",
                    error_message="SkillActivate: 'name' must be a non-empty string",
                    parent_tool_use_id=self._parent_tool_use_id,
                    agent_name=self._agent_name,
                )
                store.append_event(session_id, result)
                yield result
                return

            if skill_name not in self._active_skills:
                self._active_skills.append(skill_name)

            activated = SkillActivated(
                name=skill_name,
                parent_tool_use_id=self._parent_tool_use_id,
                agent_name=self._agent_name,
            )
            store.append_event(session_id, activated)
            yield activated

            result = ToolResult(
                tool_use_id=tool_call.tool_use_id,
                output={"active": list(self._active_skills)},
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
            child_options = OpenAgentOptions(
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
                    fetched = await tool.run(tool_input2, ToolContext(cwd=options.cwd))
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

        try:
            tool = options.tools.get(tool_name)
            output = await tool.run(tool_input2, ToolContext(cwd=options.cwd))
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
