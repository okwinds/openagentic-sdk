from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oa")
    sub = parser.add_subparsers(dest="command")

    p_chat = sub.add_parser("chat", help="Start a multi-turn chat REPL")
    p_chat.add_argument("--resume", dest="session_id", default=None, help="Resume an existing session id")

    p_run = sub.add_parser("run", help="Run a one-shot prompt")
    p_run.add_argument("prompt", help="Prompt text")
    p_run.add_argument("--json", action="store_true", help="Emit JSON output")
    p_run.add_argument("--stream", dest="stream", action="store_true", default=True, help="Stream output")
    p_run.add_argument("--no-stream", dest="stream", action="store_false", help="Disable streaming output")

    p_resume = sub.add_parser("resume", help="Resume an existing session")
    p_resume.add_argument("session_id", help="Session id to resume")

    p_logs = sub.add_parser("logs", help="Summarize session events")
    p_logs.add_argument("session_id", help="Session id to summarize")
    p_logs.add_argument(
        "--session-root",
        default=None,
        help="Session root directory (default: ~/.openagentic-sdk; env: OPENAGENTIC_SDK_HOME; legacy: OPEN_AGENT_SDK_HOME)",
    )

    return parser


def parse_args(argv: list[str]) -> argparse.Namespace:
    return build_parser().parse_args(argv)
