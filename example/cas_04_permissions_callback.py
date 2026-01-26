from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

from _common import example_artifact_dir, example_offline_enabled, repo_root, rightcode_options

from openagentic_sdk import AssistantMessage, TextBlock, query_messages
from openagentic_sdk.permissions.cas import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext
from openagentic_sdk.permissions.gate import PermissionGate


def _print_assistant_text(msg: object) -> None:
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                text = (block.text or "").strip()
                if text:
                    print(text)


async def main() -> None:
    print("=== CAS Scenario: tool permission callback (allow/deny/rewrite) ===")
    out_dir = example_artifact_dir("cas_04")
    token = os.environ.get("OPENAGENTIC_CAS_TOKEN") or "PERMISSION_CALLBACK_TOKEN"

    callback_log: list[tuple[str, dict[str, Any]]] = []

    async def can_use_tool(
        tool_name: str,
        input_data: dict[str, Any],
        context: ToolPermissionContext,  # noqa: ARG001
    ) -> PermissionResultAllow | PermissionResultDeny:
        callback_log.append((tool_name, dict(input_data)))

        if tool_name in {"Read", "Glob", "Grep", "Skill", "SlashCommand"}:
            return PermissionResultAllow()

        if tool_name in {"Write", "Edit", "NotebookEdit"}:
            file_path = input_data.get("file_path", input_data.get("filePath", ""))
            if isinstance(file_path, str) and (file_path.startswith("/etc/") or file_path.startswith("/usr/")):
                return PermissionResultDeny(message=f"Refusing to write system path: {file_path}")

            # Redirect non-relative writes into a safe folder inside cwd.
            if isinstance(file_path, str) and not (file_path.startswith("./") or file_path.startswith("../")):
                redirected = f"./safe_output/{Path(file_path).name}"
                updated = dict(input_data)
                updated["file_path"] = redirected
                return PermissionResultAllow(updated_input=updated)

            return PermissionResultAllow()

        if tool_name == "Bash":
            cmd = input_data.get("command", "")
            if isinstance(cmd, str) and any(bad in cmd for bad in ("rm -rf", "mkfs", "dd if=", "sudo ")):
                return PermissionResultDeny(message="Refusing dangerous bash command")
            return PermissionResultAllow()

        return PermissionResultAllow()

    base = rightcode_options(cwd=out_dir, project_dir=repo_root(), allowed_tools=["Write", "Read"])
    gate = PermissionGate(permission_mode="default", can_use_tool=can_use_tool, interactive=False)
    options = replace(base, permission_gate=gate, allowed_tools=["Write", "Read"], max_steps=25)

    prompt = (
        "Do the following steps using tools:\n"
        "1) Create hello.txt containing exactly this token:\n"
        f"{token}\n"
        "2) Read hello.txt and reply with exactly the token.\n"
    )

    async for msg in query_messages(prompt=prompt, options=options):
        _print_assistant_text(msg)

    if not example_offline_enabled():
        safe_path = out_dir / "safe_output" / "hello.txt"
        if safe_path.exists():
            print(f"\nWrote (redirected): {safe_path}")
        else:
            print(f"\nNote: expected redirected file not found: {safe_path}")

    if callback_log:
        print("\nCallback saw tool requests (order):")
        print(", ".join(name for name, _ in callback_log))


if __name__ == "__main__":
    asyncio.run(main())

