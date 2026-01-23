from __future__ import annotations

import asyncio
from pathlib import Path

from _common import EventPrinter, example_artifact_dir, example_debug_enabled, require_command, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    require_command("bash", help="This example uses the Bash tool which shells out to `bash -lc`. Install bash (WSL/Git Bash) and rerun.")

    out_dir = example_artifact_dir("35")
    p = out_dir / "calc.py"
    p.write_text(
        "def add(a,b):\n"
        "    return a+b\n"
        "\n"
        "def main():\n"
        "    print(add(1,2))\n"
        "\n"
        "if __name__=='__main__':\n"
        "    main()\n",
        encoding="utf-8",
    )

    options = rightcode_options(
        cwd=out_dir,
        project_dir=out_dir,
        allowed_tools=["Read", "Edit", "Bash"],
        permission_mode="bypass",
        interactive=False,
    )
    prompt = (
        "Refactor and verify.\n"
        "1) Use Read to inspect calc.py.\n"
        "2) Use Edit to format and add type hints (keep behavior same).\n"
        "3) Use Bash: python -m py_compile calc.py\n"
        "4) Use Bash: python calc.py\n"
        "Finally reply with REFACTOR_OK."
    )
    printer = EventPrinter(debug=example_debug_enabled())
    async for ev in query(prompt=prompt, options=options):
        printer.on_event(ev)

    print(f"Wrote: {p}")
    if example_debug_enabled():
        print(f"[debug] calc.py now:\n{p.read_text(encoding='utf-8', errors='replace')}")


if __name__ == "__main__":
    asyncio.run(main())
