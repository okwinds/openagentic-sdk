from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from open_agent_sdk.sessions.store import FileSessionStore

from .args import build_parser
from .config import build_options
from .logs_cmd import summarize_events
from .repl import run_chat
from .run_cmd import run_once
from .style import StyleConfig


def default_permission_mode() -> str:
    return os.getenv("OA_PERMISSION_MODE") or "default"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    if getattr(ns, "command", None) is None:
        parser.print_help()
        return 0

    cwd = os.getcwd()
    project_dir = cwd
    permission_mode = default_permission_mode()
    interactive = bool(getattr(sys.stdin, "isatty", lambda: False)())
    style = StyleConfig(color="auto")

    if ns.command in ("chat", "resume"):
        session_id = getattr(ns, "session_id", None)
        opts = build_options(
            cwd=cwd,
            project_dir=project_dir,
            permission_mode=permission_mode,
            resume=session_id,
            interactive=interactive,
        )
        return int(
            asyncio.run(
                run_chat(
                    opts,
                    color_config=style,
                    debug=False,
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                )
            )
        )

    if ns.command == "run":
        opts = build_options(
            cwd=cwd,
            project_dir=project_dir,
            permission_mode=permission_mode,
            interactive=interactive,
        )
        prompt = str(getattr(ns, "prompt", "") or "")
        stream = bool(getattr(ns, "stream", True))
        json_output = bool(getattr(ns, "json", False))
        return int(asyncio.run(run_once(opts, prompt, stream=stream, json_output=json_output, color_config=style)))

    if ns.command == "logs":
        root = getattr(ns, "session_root", None)
        if root:
            root_dir = Path(str(root)).expanduser()
        else:
            env = os.environ.get("OPEN_AGENT_SDK_HOME")
            root_dir = Path(env).expanduser() if env else Path.home() / ".open-agent-sdk"
        store = FileSessionStore(root_dir=root_dir)
        sid = str(getattr(ns, "session_id", "") or "")
        events = store.read_events(sid)
        text = summarize_events(events, color_config=style, isatty=sys.stdout.isatty(), platform=sys.platform)
        sys.stdout.write(text)
        sys.stdout.flush()
        return 0

    parser.error(f"command not implemented: {ns.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
