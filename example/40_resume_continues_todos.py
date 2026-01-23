from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

from _common import repo_root, rightcode_options
from openagentic_sdk.console import console_debug_enabled, console_run


async def main() -> None:
    options1 = rightcode_options(
        cwd=repo_root(),
        project_dir=repo_root(),
        allowed_tools=["TodoWrite"],
        permission_mode="bypass",
        interactive=False,
    )
    r1 = await console_run(
        prompt="Create 3 TODOs for 'clean up the repo'. Use TodoWrite. Then say RESUME_TODO_1_OK.",
        options=options1,
    )
    print(r1.final_text)
    session_id = r1.session_id
    print(f"session_id={session_id}")

    options2 = replace(options1, resume=session_id)
    r2 = await console_run(prompt="Update the TODOs: mark one completed via TodoWrite. Then say RESUME_TODO_2_OK.", options=options2)
    print(r2.final_text)

    # Show where the runtime persisted the todos.
    session_root = Path(options1.session_root) if options1.session_root else (repo_root() / ".openagentic-sdk")
    todo_file = session_root / "sessions" / session_id / "todos.json"
    print(f"todos_path={todo_file}")
    if console_debug_enabled() and todo_file.exists():
        data = json.loads(todo_file.read_text(encoding="utf-8"))
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
