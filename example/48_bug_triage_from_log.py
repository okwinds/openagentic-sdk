from __future__ import annotations

import asyncio

from _common import example_artifact_dir, repo_root, rightcode_options
from openagentic_sdk.console import console_run


PROMPT = """\
You are given an error log snippet. Triage it like an SDK maintainer.

Goals:
- Identify likely root cause(s)
- Point to relevant files and functions in this repo
- Suggest a minimal fix strategy
- Provide a short checklist to confirm the fix

Use tools (Grep/Read) to locate relevant code.

Output: write a Markdown triage note to the path I give you.
"""


ERROR_LOG = """\
Traceback (most recent call last):
  File "example.py", line 10, in <module>
    raise RuntimeError("Example error: previous_response_id missing")
RuntimeError: Example error: previous_response_id missing
"""


async def main() -> None:
    root = repo_root()
    artifacts = example_artifact_dir("48")
    out_path = artifacts / "triage.md"

    options = rightcode_options(
        cwd=root,
        project_dir=root,
        allowed_tools=None,
        permission_mode="bypass",
        interactive=True,
    )

    prompt = f"{PROMPT}\n\nError log:\n```\n{ERROR_LOG}\n```\n\nWrite to: {out_path}"
    r = await console_run(prompt=prompt, options=options)

    print("Wrote triage note:")
    print(str(out_path))
    print()
    print("Assistant final text:")
    print(r.final_text)


if __name__ == "__main__":
    asyncio.run(main())
