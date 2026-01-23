from __future__ import annotations

import asyncio
from pathlib import Path

from _common import example_artifact_dir, repo_root, require_command, rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    require_command("bash", help="This example uses the Bash tool which shells out to `bash -lc`. Install bash (WSL/Git Bash) and rerun.")
    require_command("git", help="This example runs `git log`. Install git and rerun.")

    out_dir = example_artifact_dir("31")
    options = rightcode_options(
        cwd=out_dir,
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
    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt=prompt, options=options, renderer=printer)

    out_path = out_dir / "CHANGELOG_SNIPPET.md"
    if out_path.exists():
        print(f"Wrote: {out_path}")
    else:
        print(f"Expected changelog at: {out_path} (but it was not created)")


if __name__ == "__main__":
    asyncio.run(main())
