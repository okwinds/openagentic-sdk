from __future__ import annotations

import asyncio

from _common import example_artifact_dir, repo_root, rightcode_options
from openagentic_sdk.console import console_run


PROMPT = """\
You're onboarding onto a new codebase.

Task:
- Inspect this repository quickly using tools (Glob/Grep/Read).
- Produce a short onboarding report:
  - What the project is and who it's for
  - How to run tests / examples locally
  - Key directories and responsibilities
  - A suggested 'first file to read'
  - 3 risks / sharp edges (APIs, security, or maintenance)

Output: write a Markdown report to the path I give you.
"""


async def main() -> None:
    root = repo_root()
    artifacts = example_artifact_dir("46")
    out_path = artifacts / "onboarding.md"

    options = rightcode_options(
        cwd=root,
        project_dir=root,
        allowed_tools=None,
        permission_mode="bypass",
        interactive=True,
    )

    prompt = f"{PROMPT}\nWrite to: {out_path}"
    r = await console_run(prompt=prompt, options=options)

    print("Wrote onboarding report:")
    print(str(out_path))
    print()
    print("Assistant final text (may be brief if it only confirms the write):")
    print(r.final_text)


if __name__ == "__main__":
    asyncio.run(main())
