from __future__ import annotations

import asyncio
from pathlib import Path

from _common import EventPrinter, example_artifact_dir, example_debug_enabled, require_command, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    require_command("bash", help="This example uses the Bash tool which shells out to `bash -lc`. Install bash (WSL/Git Bash) and rerun.")

    out_dir = example_artifact_dir("32")
    bad = out_dir / "bad.py"
    bad.write_text("def oops(:\n    pass\n", encoding="utf-8")

    options = rightcode_options(
        cwd=out_dir,
        project_dir=out_dir,
        allowed_tools=["Read", "Edit", "Bash"],
        permission_mode="bypass",
        interactive=False,
    )
    prompt = (
        "Fix a build error.\n"
        "1) Use Bash to run: python -m py_compile bad.py (it should fail)\n"
        "2) Use Read to inspect bad.py\n"
        "3) Use Edit to fix the syntax error\n"
        "4) Use Bash to run: python -m py_compile bad.py again (it should pass)\n"
        "Finally reply with TRIAGE_OK."
    )
    printer = EventPrinter(debug=example_debug_enabled())
    async for ev in query(prompt=prompt, options=options):
        printer.on_event(ev)

    print(f"Wrote: {bad}")
    if example_debug_enabled():
        print(f"[debug] bad.py now:\n{bad.read_text(encoding='utf-8', errors='replace')}")


if __name__ == "__main__":
    asyncio.run(main())
