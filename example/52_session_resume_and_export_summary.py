from __future__ import annotations

import asyncio
from dataclasses import replace

from _common import example_artifact_dir, repo_root, rightcode_options
from openagentic_sdk.console import console_run


TURN_1 = """\
Start a new session.
- Tell me what this repository is.
- Mention 2-3 key features.
Keep it brief.
"""


TURN_2 = """\
You should have prior context (this is a resumed session).
Now write a short session summary including:
- What we learned
- What files we inspected
- What next steps you'd recommend

Write to the path I give you.
"""


async def main() -> None:
    root = repo_root()
    artifacts = example_artifact_dir("52")
    out_path = artifacts / "session_summary.md"

    options1 = rightcode_options(
        cwd=root,
        project_dir=root,
        allowed_tools=None,
        permission_mode="acceptEdits",
        interactive=True,
    )

    r1 = await console_run(prompt=TURN_1, options=options1)
    print("Turn 1 complete.")
    print(f"session_id={r1.session_id}")
    print()

    options2 = rightcode_options(
        cwd=root,
        project_dir=root,
        allowed_tools=None,
        permission_mode="acceptEdits",
        interactive=True,
    )
    options2 = replace(options2, resume=r1.session_id)

    r2 = await console_run(prompt=f"{TURN_2}\nWrite to: {out_path}", options=options2)

    print("Wrote session summary:")
    print(str(out_path))
    print()
    print("Assistant final text:")
    print(r2.final_text)


if __name__ == "__main__":
    asyncio.run(main())
