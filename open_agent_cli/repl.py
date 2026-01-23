from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import TextIO

from open_agent_sdk.client import OpenAgentSDKClient
from open_agent_sdk.console.renderer import ConsoleRenderer
from open_agent_sdk.console.run import console_client_turn
from open_agent_sdk.options import OpenAgentOptions
from open_agent_sdk.skills.index import index_skills

from .style import StyleConfig, bold, dim, fg_green, fg_red, should_colorize


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


async def run_chat(
    options: OpenAgentOptions,
    *,
    color_config: StyleConfig,
    debug: bool,
    stdin: TextIO,
    stdout: TextIO,
) -> int:
    enable_color = should_colorize(color_config, isatty=getattr(stdout, "isatty", lambda: False)(), platform=__import__("sys").platform)

    renderer = ConsoleRenderer(debug=debug)
    client = OpenAgentSDKClient(options)
    turn = 0

    _print(stdout, dim("Type /help for commands.", enabled=enable_color))
    while True:
        stdout.write(fg_green("oa> ", enabled=enable_color))
        stdout.flush()
        line = stdin.readline()
        if line == "":
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
                renderer = ConsoleRenderer(debug=debug)
                _print(stdout, dim(f"debug={'on' if debug else 'off'}", enabled=enable_color))
                continue
            if name == "interrupt":
                await client.interrupt()
                _print(stdout, dim("interrupt signaled", enabled=enable_color))
                continue
            if name == "new":
                await client.disconnect()
                client = OpenAgentSDKClient(replace(options, resume=None))
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

        try:
            turn += 1
            await client.connect()
            await console_client_turn(client=client, prompt=prompt, renderer=renderer)
        except KeyboardInterrupt:
            await client.interrupt()
            _print(stdout, dim("interrupted", enabled=enable_color))
            continue
        except SystemExit as e:
            _print(stdout, fg_red(str(e), enabled=enable_color))
            return 1
        except Exception as e:  # noqa: BLE001
            _print(stdout, fg_red(str(e), enabled=enable_color))
            return 1

