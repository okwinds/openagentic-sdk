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
        help="Session root directory (default: ~/.openagentic-sdk; env: OPENAGENTIC_SDK_HOME)",
    )

    p_mcp = sub.add_parser("mcp", help="Manage MCP servers and credentials")
    mcp_sub = p_mcp.add_subparsers(dest="mcp_command")

    p_mcp_list = mcp_sub.add_parser("list", help="List MCP servers from config")
    _ = p_mcp_list

    p_mcp_auth = mcp_sub.add_parser("auth", help="Store a bearer token for a remote MCP server")
    p_mcp_auth.add_argument("name", help="MCP server name (key under config.mcp)")
    p_mcp_auth.add_argument("--token", required=True, help="Bearer token")

    p_mcp_logout = mcp_sub.add_parser("logout", help="Clear stored credentials for an MCP server")
    p_mcp_logout.add_argument("name", help="MCP server name (key under config.mcp)")

    p_share = sub.add_parser("share", help="Share a session (offline/local by default)")
    p_share.add_argument("session_id", help="Session id to share")
    p_share.add_argument(
        "--session-root",
        default=None,
        help="Session root directory (default: ~/.openagentic-sdk; env: OPENAGENTIC_SDK_HOME)",
    )

    p_unshare = sub.add_parser("unshare", help="Remove a shared session payload")
    p_unshare.add_argument("share_id", help="Share id to remove")

    p_shared = sub.add_parser("shared", help="Print a shared session payload")
    p_shared.add_argument("share_id", help="Share id to fetch")

    return parser


def parse_args(argv: list[str]) -> argparse.Namespace:
    return build_parser().parse_args(argv)
