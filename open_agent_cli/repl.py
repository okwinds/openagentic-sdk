from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
from dataclasses import replace
from typing import TextIO

from open_agent_sdk.options import OpenAgentOptions
from open_agent_sdk.runtime import AgentRuntime
from open_agent_sdk.sessions.store import FileSessionStore
from open_agent_sdk.skills.index import index_skills

from .style import (
    ANSI_BG_GRAY,
    ANSI_FG_DEFAULT,
    ANSI_FG_GREEN,
    ANSI_RESET,
    InlineCodeHighlighter,
    StyleConfig,
    StylizingStream,
    bold,
    dim,
    fg_red,
    should_colorize,
)
from .trace import TraceRenderer


def parse_repl_command(line: str) -> tuple[str, str] | None:
    s = line.strip()
    if not s.startswith("/"):
        return None
    s = s[1:].strip()
    if not s:
        return None
    parts = s.split(None, 1)
    name = parts[0].strip()
    arg = parts[1].strip() if len(parts) > 1 else ""
    return name, arg


def _print(stdout: TextIO, text: str) -> None:
    stdout.write(text)
    if not text.endswith("\n"):
        stdout.write("\n")
    stdout.flush()


_CWD_QUESTION_RE = re.compile(
    r"^\s*(?:当前目录(?:是|为)?|当前路径|pwd|where am i|current directory)\s*[?？]?\s*$",
    re.IGNORECASE,
)


async def run_chat(
    options: OpenAgentOptions,
    *,
    color_config: StyleConfig,
    debug: bool,
    stdin: TextIO,
    stdout: TextIO,
) -> int:
    enable_color = should_colorize(color_config, isatty=getattr(stdout, "isatty", lambda: False)(), platform=sys.platform)
    show_thinking_hint = os.getenv("OA_SHOW_THINKING", "1").strip().lower() not in ("0", "false", "no", "off")
    is_tty = bool(getattr(stdout, "isatty", lambda: False)())
    trace_enabled = os.getenv("OA_TRACE", "1").strip().lower() not in ("0", "false", "no", "off")

    render_stream = StylizingStream(stdout, highlighter=InlineCodeHighlighter(enabled=enable_color)) if enable_color else stdout
    renderer = TraceRenderer(stream=render_stream, color=enable_color, show_hooks=debug) if trace_enabled else TraceRenderer(stream=render_stream, color=False, show_hooks=debug)
    turn = 0

    store = options.session_store
    if store is None:
        root = options.session_root
        if root is None:
            env = os.environ.get("OPEN_AGENT_SDK_HOME")
            root = os.path.expanduser(env) if env else os.path.join(os.path.expanduser("~"), ".open-agent-sdk")
        store = FileSessionStore(root_dir=__import__("pathlib").Path(root))
    opts = replace(options, session_store=store)
    session_id = opts.resume
    current_abort_event: asyncio.Event | None = None

    _print(stdout, dim("Type /help for commands.", enabled=enable_color))
    while True:
        prompt = "oa> "
        if enable_color:
            cols = int(shutil.get_terminal_size(fallback=(80, 24)).columns)

            # Add some vertical padding for the input area: one blank gray line above.
            stdout.write(ANSI_BG_GRAY + (" " * cols) + ANSI_RESET + "\n")

            # Render the prompt on a full-width gray background while keeping the cursor
            # right after the prompt (so the user types on the gray line).
            styled_prompt = f"{ANSI_BG_GRAY}{ANSI_FG_GREEN}{prompt}{ANSI_FG_DEFAULT}"
            fill = " " * max(0, cols - len(prompt))
            if fill:
                stdout.write(styled_prompt + fill + "\r" + styled_prompt)
            else:
                stdout.write(styled_prompt)
            stdout.flush()
        else:
            stdout.write(prompt)
            stdout.flush()

        try:
            line = stdin.readline()
        except KeyboardInterrupt:
            if enable_color:
                stdout.write(ANSI_RESET + "\n")
                stdout.flush()
            continue
        if enable_color:
            # Add one blank gray line below the user's input ("margin-bottom"), then
            # reset so subsequent model output has no background.
            cols = int(shutil.get_terminal_size(fallback=(80, 24)).columns)
            stdout.write(ANSI_BG_GRAY + (" " * cols) + ANSI_RESET + "\n")
            stdout.flush()
        if line == "":
            if enable_color:
                stdout.write(ANSI_RESET)
                stdout.flush()
            _print(stdout, "")
            return 0

        cmd = parse_repl_command(line)
        if cmd is not None:
            name, arg = cmd
            if name in ("exit", "quit"):
                return 0
            if name == "help":
                _print(
                    stdout,
                    "\n".join(
                        [
                            bold("Commands:", enabled=enable_color),
                            "  /help",
                            "  /exit",
                            "  /new",
                            "  /interrupt",
                            "  /debug",
                            "  /skills",
                            "  /skill <name>",
                            "  /cmd <name>",
                        ]
                    ),
                )
                continue
            if name == "debug":
                debug = not debug
                _print(stdout, dim(f"debug={'on' if debug else 'off'}", enabled=enable_color))
                continue
            if name == "interrupt":
                if current_abort_event is not None:
                    current_abort_event.set()
                _print(stdout, dim("interrupt signaled", enabled=enable_color))
                continue
            if name == "new":
                session_id = None
                opts = replace(opts, resume=None)
                turn = 0
                _print(stdout, dim("started new session", enabled=enable_color))
                continue
            if name == "skills":
                project_dir = options.project_dir or options.cwd
                skills = index_skills(project_dir=str(project_dir))
                if not skills:
                    _print(stdout, "(no skills found)")
                else:
                    for s in skills:
                        _print(stdout, f"- {s.name}: {s.description}".rstrip())
                continue
            if name == "skill":
                if not arg:
                    _print(stdout, fg_red("usage: /skill <name>", enabled=enable_color))
                    continue
                line = f"执行技能 {arg}"
            elif name == "cmd":
                if not arg:
                    _print(stdout, fg_red("usage: /cmd <name>", enabled=enable_color))
                    continue
                line = f"Run slash command {arg}"
            else:
                _print(stdout, fg_red(f"unknown command: /{name}", enabled=enable_color))
                continue

        prompt = line.rstrip("\n")
        if not prompt.strip():
            continue
        if _CWD_QUESTION_RE.match(prompt):
            _print(stdout, f"当前目录：{options.cwd}")
            continue

        try:
            turn += 1
            if show_thinking_hint and is_tty:
                _print(stdout, dim("thinking…", enabled=enable_color))

            abort_event = asyncio.Event()
            current_abort_event = abort_event
            run_opts = replace(opts, resume=session_id, abort_event=abort_event)
            runtime = AgentRuntime(run_opts)
            async for ev in runtime.query(prompt):
                if getattr(ev, "type", None) == "system.init":
                    sid = getattr(ev, "session_id", None)
                    if isinstance(sid, str) and sid:
                        session_id = sid
                renderer.on_event(ev)
            current_abort_event = None
            if session_id:
                opts = replace(opts, resume=session_id)
        except KeyboardInterrupt:
            if current_abort_event is not None:
                current_abort_event.set()
            _print(stdout, dim("interrupted", enabled=enable_color))
            continue
        except SystemExit as e:
            _print(stdout, fg_red(str(e), enabled=enable_color))
            return 1
        except Exception as e:  # noqa: BLE001
            _print(stdout, fg_red(str(e), enabled=enable_color))
            return 1
