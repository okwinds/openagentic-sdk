from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, repo_root, require_command, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    require_command("bash", help="This example uses the Bash tool which shells out to `bash -lc`. Install bash (WSL/Git Bash) and rerun.")
    require_command("git", help="This example runs `git log`. Install git and rerun.")

    with TemporaryDirectory() as td:
        root = Path(td)
        options = rightcode_options(
            cwd=root,
            project_dir=repo_root(),
            allowed_tools=["Bash", "Write"],
            permission_mode="bypass",
            interactive=False,
        )
        repo = str(repo_root())
        prompt = (
            "Generate a tiny changelog snippet.\n"
            f"1) Use Bash to run: git -C '{repo}' log -10 --oneline\n"
            "2) Use Write to create CHANGELOG_SNIPPET.md summarizing the last 10 commits in 5 bullets.\n"
            "Finally reply with CHANGELOG_OK."
        )
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)

        if (root / "CHANGELOG_SNIPPET.md").exists():
            print(f"Wrote: {root / 'CHANGELOG_SNIPPET.md'}")


if __name__ == "__main__":
    asyncio.run(main())

