from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, TextIO


def console_debug_enabled(argv: list[str] | None = None) -> bool:
    argv2 = sys.argv[1:] if argv is None else argv
    env = os.environ.get("OPENAGENTIC_SDK_CONSOLE_DEBUG") or os.environ.get("OPENAGENTIC_SDK_EXAMPLE_DEBUG") or ""
    return env.strip().lower() in ("1", "true", "yes", "y", "on") or ("--debug" in argv2)


def _safe_json_loads(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _render_skill_list(skills: Any) -> list[str]:
    if not isinstance(skills, list) or not skills:
        return []
    lines: list[str] = []
    for s in skills:
        if not isinstance(s, dict):
            continue
        name = s.get("name") if isinstance(s.get("name"), str) else ""
        desc = s.get("description") if isinstance(s.get("description"), str) else ""
        summary = s.get("summary") if isinstance(s.get("summary"), str) else ""
        blurb = desc or summary
        if name and blurb:
            lines.append(f"- `{name}` — {blurb}")
        elif name:
            lines.append(f"- `{name}`")
    return lines


def _render_skill_use_line(tool_input: Any) -> str | None:
    if not isinstance(tool_input, dict):
        return None
    action = tool_input.get("action")
    name = tool_input.get("name")
    action2 = str(action).strip().lower() if isinstance(action, str) else ""
    name2 = str(name).strip() if isinstance(name, str) else ""
    if not action2:
        action2 = "load" if name2 else "list"
    if action2 == "list":
        return "正在列出Skills...\n"
    if action2 in ("load", "get", "read") and name2:
        return f"正在执行Skill：{name2}...\n"
    return "正在执行Skill...\n"


def _render_skill_loaded_line(output: Any) -> str | None:
    if not isinstance(output, dict):
        return None
    name = output.get("name")
    if isinstance(name, str) and name.strip():
        return f"Skill已加载：{name.strip()}\n"
    return None


@dataclass
class ConsoleRenderer:
    stream: TextIO = sys.stdout
    debug: bool = False
    _saw_delta: bool = False
    _tool_use_names: dict[str, str] = field(default_factory=dict)
    _todo_inputs: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def on_event(self, ev: Any) -> None:
        t = getattr(ev, "type", None)
        if t == "assistant.delta":
            delta = getattr(ev, "text_delta", "")
            if isinstance(delta, str) and delta:
                self.stream.write(delta)
                self.stream.flush()
                self._saw_delta = True
            return

        if t == "assistant.message":
            if self._saw_delta:
                self.stream.write("\n")
                self.stream.flush()
                self._saw_delta = False
                return
            text = getattr(ev, "text", "")
            if isinstance(text, str) and text:
                agent = getattr(ev, "agent_name", None)
                prefix = f"[{agent}] " if isinstance(agent, str) and agent else ""
                self.stream.write(prefix + text + "\n")
                self.stream.flush()
            return

        if t == "user.question":
            prompt = getattr(ev, "prompt", "")
            choices = getattr(ev, "choices", None)
            if isinstance(prompt, str) and prompt:
                if isinstance(choices, list) and choices:
                    self.stream.write(f"[question] {prompt} choices={choices}\n")
                else:
                    self.stream.write(f"[question] {prompt}\n")
                self.stream.flush()
            return

        if t == "tool.use":
            tool_use_id = getattr(ev, "tool_use_id", "")
            name = getattr(ev, "name", "")
            tool_input = getattr(ev, "input", None)
            if isinstance(tool_use_id, str) and tool_use_id and isinstance(name, str) and name:
                self._tool_use_names[tool_use_id] = name
                if name == "TodoWrite" and isinstance(tool_input, dict):
                    todos = tool_input.get("todos")
                    if isinstance(todos, list):
                        self._todo_inputs[tool_use_id] = [dict(x) for x in todos if isinstance(x, dict)]

            if not self.debug:
                if name == "Skill":
                    line = _render_skill_use_line(tool_input)
                    if line:
                        self.stream.write(line)
                        self.stream.flush()
                return
            agent = getattr(ev, "agent_name", None)
            prefix = f"[{agent}] " if isinstance(agent, str) and agent else ""
            if isinstance(name, str) and name:
                if isinstance(tool_input, dict) and tool_input:
                    self.stream.write(f"{prefix}[tool] {name} {tool_input}\n")
                else:
                    self.stream.write(f"{prefix}[tool] {name}\n")
                self.stream.flush()
            return

        if t == "tool.result" and not self.debug:
            tool_use_id = getattr(ev, "tool_use_id", "")
            if not isinstance(tool_use_id, str) or not tool_use_id:
                return
            tool_name = self._tool_use_names.get(tool_use_id)

            if tool_name == "TodoWrite":
                output = getattr(ev, "output", None)
                stats = output.get("stats") if isinstance(output, dict) else None
                if isinstance(stats, dict):
                    self.stream.write(
                        "TODOs: "
                        f"total={stats.get('total')} "
                        f"pending={stats.get('pending')} "
                        f"in_progress={stats.get('in_progress')} "
                        f"completed={stats.get('completed')}\n"
                    )
                else:
                    self.stream.write("TODOs updated\n")
                for item in self._todo_inputs.get(tool_use_id) or []:
                    status = item.get("status") if isinstance(item.get("status"), str) else "pending"
                    active = item.get("activeForm") or item.get("content") or ""
                    self.stream.write(f"- [{status}] {active}\n")
                self.stream.flush()
                return

            if tool_name == "Skill":
                if bool(getattr(ev, "is_error", False)):
                    error_message = getattr(ev, "error_message", None)
                    msg = error_message if isinstance(error_message, str) and error_message else "unknown error"
                    self.stream.write(f"Skill执行失败：{msg}\n")
                    self.stream.flush()
                    return
                output = getattr(ev, "output", None)
                if isinstance(output, dict):
                    loaded = _render_skill_loaded_line(output)
                    if loaded:
                        self.stream.write(loaded)
                    lines = _render_skill_list(output.get("skills"))
                    if lines:
                        self.stream.write("Available skills:\n")
                        for ln in lines:
                            self.stream.write(ln + "\n")
                        self.stream.flush()
                return

            return

        if not self.debug:
            return

        if t == "tool.result":
            tool_use_id = getattr(ev, "tool_use_id", "")
            is_error = bool(getattr(ev, "is_error", False))
            error_message = getattr(ev, "error_message", None)
            status = "error" if is_error else "ok"
            line = f"[tool.result] {tool_use_id} {status}".strip()
            if is_error and isinstance(error_message, str) and error_message:
                line += f" msg={error_message!r}"
            self.stream.write(line + "\n")
            self.stream.flush()
            return

        if t == "hook.event":
            name = getattr(ev, "name", "")
            hook_point = getattr(ev, "hook_point", "")
            action = getattr(ev, "action", None)
            matched = getattr(ev, "matched", None)
            line = f"[hook] {hook_point}:{name}"
            if action is not None:
                line += f" action={action}"
            if matched is not None:
                line += f" matched={matched}"
            self.stream.write(line + "\n")
            self.stream.flush()
            return

        if t == "skill.activated":
            name = getattr(ev, "name", "")
            if isinstance(name, str) and name:
                self.stream.write(f"[skill] activated {name}\n")
                self.stream.flush()
            return

        if t == "result":
            stop_reason = getattr(ev, "stop_reason", None)
            session_id = getattr(ev, "session_id", None)
            line = "[done]"
            if isinstance(stop_reason, str) and stop_reason:
                line += f" stop_reason={stop_reason}"
            if isinstance(session_id, str) and session_id:
                line += f" session_id={session_id}"
            self.stream.write(line + "\n")
            self.stream.flush()
            return

    def on_message(self, msg: Any) -> None:
        # Supports openagentic_sdk.messages.* structures without importing them here.
        cls = msg.__class__.__name__
        if cls == "StreamEvent":
            event = getattr(msg, "event", None)
            if isinstance(event, dict) and event.get("type") == "text_delta":
                delta = event.get("delta")
                if isinstance(delta, str) and delta:
                    self.stream.write(delta)
                    self.stream.flush()
                    self._saw_delta = True
            return

        if cls == "AssistantMessage":
            content = getattr(msg, "content", None)
            if not isinstance(content, list):
                return
            for b in content:
                bcls = b.__class__.__name__
                if bcls == "TextBlock":
                    text = getattr(b, "text", "")
                    if isinstance(text, str) and text:
                        if self._saw_delta:
                            # Streaming already printed the full text via StreamEvent deltas.
                            self.stream.write("\n")
                            self.stream.flush()
                            self._saw_delta = False
                            continue
                        self.stream.write(text + "\n")
                        self.stream.flush()
                elif bcls == "ToolUseBlock":
                    tool_use_id = getattr(b, "id", "")
                    name = getattr(b, "name", "")
                    tool_input = getattr(b, "input", None)
                    if isinstance(tool_use_id, str) and tool_use_id and isinstance(name, str) and name:
                        self._tool_use_names[tool_use_id] = name
                        if name == "TodoWrite" and isinstance(tool_input, dict):
                            todos = tool_input.get("todos")
                            if isinstance(todos, list):
                                self._todo_inputs[tool_use_id] = [dict(x) for x in todos if isinstance(x, dict)]
                        if not self.debug and name == "Skill":
                            line = _render_skill_use_line(tool_input)
                            if line:
                                self.stream.write(line)
                                self.stream.flush()
                        if self.debug:
                            self.stream.write(f"[tool] {name} {tool_input}\n")
                            self.stream.flush()
                elif bcls == "ToolResultBlock":
                    tool_use_id = getattr(b, "tool_use_id", "")
                    is_error = getattr(b, "is_error", None)
                    raw = getattr(b, "content", None)
                    text = raw if isinstance(raw, str) else None
                    out = _safe_json_loads(text)
                    if isinstance(tool_use_id, str) and tool_use_id and self._tool_use_names.get(tool_use_id) == "TodoWrite":
                        stats = out.get("stats")
                        if isinstance(stats, dict):
                            self.stream.write(
                                "TODOs: "
                                f"total={stats.get('total')} "
                                f"pending={stats.get('pending')} "
                                f"in_progress={stats.get('in_progress')} "
                                f"completed={stats.get('completed')}\n"
                            )
                        else:
                            self.stream.write("TODOs updated\n")
                        for item in self._todo_inputs.get(tool_use_id) or []:
                            status = item.get("status") if isinstance(item.get("status"), str) else "pending"
                            active = item.get("activeForm") or item.get("content") or ""
                            self.stream.write(f"- [{status}] {active}\n")
                        self.stream.flush()
                    elif isinstance(tool_use_id, str) and tool_use_id and self._tool_use_names.get(tool_use_id) == "Skill":
                        if bool(is_error):
                            self.stream.write("Skill执行失败\n")
                            self.stream.flush()
                            continue
                        loaded = _render_skill_loaded_line(out)
                        if loaded:
                            self.stream.write(loaded)
                        lines = _render_skill_list(out.get("skills"))
                        if lines:
                            self.stream.write("Available skills:\n")
                            for ln in lines:
                                self.stream.write(ln + "\n")
                            self.stream.flush()
                    elif self.debug:
                        self.stream.write(f"[tool.result] {tool_use_id} error={bool(is_error)}\n")
                        self.stream.flush()
            return

        if cls == "ResultMessage":
            if self.debug:
                session_id = getattr(msg, "session_id", None)
                is_error = bool(getattr(msg, "is_error", False))
                line = "[done]"
                if isinstance(session_id, str) and session_id:
                    line += f" session_id={session_id}"
                if is_error:
                    line += " error=True"
                self.stream.write(line + "\n")
                self.stream.flush()
            return
