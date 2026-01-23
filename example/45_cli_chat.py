from __future__ import annotations

import asyncio
import os

from _common import repo_root, rightcode_options
from openagentic_sdk.client import OpenAgentSDKClient
from openagentic_sdk.console import ConsoleRenderer, console_client_turn, console_debug_enabled


HELP = """\
Interactive CLI chat (multi-turn) for openagentic-sdk.

Commands:
  /help         Show this help
  /exit         Quit
  /new          Start a fresh session (clears context)
  /interrupt    Interrupt the current in-flight request (also works via Ctrl+C)

Tips:
  - Try: "What Skills are available?"
  - Try: "执行技能 main-process"
  - Set RIGHTCODE_API_KEY and optionally RIGHTCODE_MODEL/RIGHTCODE_BASE_URL.
  - Permission mode defaults to acceptEdits; override with OPEN_AGENT_SDK_PERMISSION_MODE.
"""


async def main() -> None:
    project_dir = repo_root() / "example"
    permission_mode = os.environ.get("OPEN_AGENT_SDK_PERMISSION_MODE", "acceptEdits")

    options = rightcode_options(
        cwd=project_dir,
        project_dir=project_dir,
        allowed_tools=None,  # allow all SDK tools
        permission_mode=permission_mode,
        interactive=True,
    )

    renderer = ConsoleRenderer(debug=console_debug_enabled())
    client: OpenAgentSDKClient = OpenAgentSDKClient(options)
    await client.connect()

    turn = 0
    print(HELP.rstrip())
    try:
        while True:
            try:
                user_input = input(f"\n[Turn {turn + 1}] You: ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            cmd = user_input.lower()
            if cmd in ("/exit", "exit", "quit"):
                break
            if cmd in ("/help", "help", "?"):
                print(HELP.rstrip())
                continue
            if cmd in ("/new", "new"):
                await client.disconnect()
                client = OpenAgentSDKClient(options)
                await client.connect()
                turn = 0
                print("Started new session (previous context cleared).")
                continue
            if cmd in ("/interrupt", "interrupt"):
                await client.interrupt()
                print("Interrupt requested.")
                continue

            try:
                await console_client_turn(client=client, prompt=user_input, renderer=renderer)
            except KeyboardInterrupt:
                await client.interrupt()
                print("\nInterrupted.")
                continue

            turn += 1
            if renderer.debug:
                print()
    finally:
        await client.disconnect()
        print(f"Conversation ended after {turn} turns.")


if __name__ == "__main__":
    asyncio.run(main())
