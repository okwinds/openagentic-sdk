from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query
from openagentic_sdk import OpenAgentOptions
from openagentic_sdk.events import UserQuestion
from openagentic_sdk.permissions.gate import PermissionGate


async def _always_yes(question: UserQuestion) -> str:
    _ = question
    return "yes"


async def _run_case(*, root: Path, label: str, gate: PermissionGate) -> None:
    print()
    print(f"=== {label} ===")
    base = rightcode_options(cwd=root, project_dir=root, allowed_tools=["Read"], interactive=False)
    options = OpenAgentOptions(
        provider=base.provider,
        model=base.model,
        api_key=base.api_key,
        cwd=base.cwd,
        session_root=base.session_root,
        project_dir=base.project_dir,
        setting_sources=base.setting_sources,
        tools=base.tools,
        allowed_tools=["Read"],
        permission_gate=gate,
    )
    prompt = "Use the Read tool to read a.txt. Then reply with NONINTERACTIVE_OK."
    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt=prompt, options=options, renderer=printer)


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.txt").write_text("hello", encoding="utf-8")

        await _run_case(
            root=root,
            label="prompt mode, no user_answerer (expected: question then PermissionDenied)",
            gate=PermissionGate(permission_mode="prompt", interactive=False),
        )
        await _run_case(
            root=root,
            label="prompt mode, user_answerer auto-yes (expected: question then tool runs)",
            gate=PermissionGate(permission_mode="prompt", interactive=False, user_answerer=_always_yes),
        )


if __name__ == "__main__":
    asyncio.run(main())
