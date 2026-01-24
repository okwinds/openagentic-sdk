from __future__ import annotations

import asyncio

from _common import example_artifact_dir, repo_root, rightcode_options
from openagentic_sdk.console import console_run


PROMPT = """\
Create a small file, but only after explicit user confirmation.

Flow:
1) First, propose the content and the target path.
2) Then ask the user a yes/no question to confirm.
3) Only if the user confirms, write the file.

Output file:
- A short developer note about what this SDK is and when to use it.
- Keep it under ~40 lines.
"""


async def main() -> None:
    root = repo_root()
    artifacts = example_artifact_dir("51")
    out_path = artifacts / "developer_note.txt"

    options = rightcode_options(
        cwd=root,
        project_dir=root,
        allowed_tools=None,
        # Prompt mode ensures tool calls are gated (and AskUserQuestion is interactive).
        permission_mode="prompt",
        interactive=True,
    )

    prompt = f"{PROMPT}\n\nTarget path: {out_path}"
    r = await console_run(prompt=prompt, options=options)

    print("If you approved, the note was written to:")
    print(str(out_path))
    print()
    print("Assistant final text:")
    print(r.final_text)


if __name__ == "__main__":
    asyncio.run(main())
