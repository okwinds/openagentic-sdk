from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options
from openagentic_sdk.console import console_run


PROMPT = """\
You are working on a Python SDK.

Task:
- Run the unit tests.
- If anything fails, identify the root cause, patch the code, and re-run tests.
- If tests already pass, make a small, low-risk improvement:
  - e.g. tighten an error message, add a tiny comment, or improve robustness
  - then re-run tests.

Constraints:
- Be conservative. Avoid wide refactors.
- Explain what you changed and why.

Note: You may use Bash to run tests, and Edit to patch files.
"""


async def main() -> None:
    root = repo_root()

    options = rightcode_options(
        cwd=root,
        project_dir=root,
        allowed_tools=None,
        permission_mode="prompt",
        interactive=True,
    )

    r = await console_run(prompt=PROMPT, options=options)
    print(r.final_text)


if __name__ == "__main__":
    asyncio.run(main())
