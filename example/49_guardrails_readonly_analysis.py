from __future__ import annotations

import asyncio

from _common import example_artifact_dir, repo_root, rightcode_options
from openagentic_sdk.console import console_run


PROMPT = """\
Work in a restricted environment.

Rules:
- You may only use read-only tools (Read/Glob/Grep).
- Do NOT use Write/Edit/Bash/Web tools.

Task:
- Analyze the repository and answer:
  - How does the runtime do tool-calls end-to-end?
  - Where is session persistence implemented?
  - Where would you add a new built-in tool?

Output:
- Write a Markdown note to the path I give you.
- Since Write is disallowed, return the Markdown in the chat response instead.
  (The caller will save it.)
"""


async def main() -> None:
    root = repo_root()
    artifacts = example_artifact_dir("49")
    out_path = artifacts / "readonly_analysis.md"

    # Only allow read-only tools, to demonstrate that the SDK can run in a
    # locked-down mode and still produce useful analysis.
    options = rightcode_options(
        cwd=root,
        project_dir=root,
        allowed_tools=["Read", "Glob", "Grep"],
        permission_mode="bypass",
        interactive=True,
    )

    prompt = f"{PROMPT}\nIntended output path (FYI only): {out_path}"
    r = await console_run(prompt=prompt, options=options)

    print("(Readonly mode) Assistant output:\n")
    print(r.final_text)


if __name__ == "__main__":
    asyncio.run(main())
