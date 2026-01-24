from __future__ import annotations

import asyncio

from _common import example_artifact_dir, repo_root, rightcode_options
from openagentic_sdk.console import console_run


PROMPT = """\
Generate an FAQ for developers who are evaluating this SDK.

Requirements:
- Use tools to read the README(s) and scan for important concepts.
- FAQ should include:
  - Setup/environment variables
  - Providers (OpenAI / compatible / Responses)
  - Session persistence and resume
  - Tools and permissions
  - Skills and .claude compatibility
  - Common pitfalls and troubleshooting

Output: write a Markdown file to the path I give you.
Keep it practical and concise.
"""


async def main() -> None:
    root = repo_root()
    artifacts = example_artifact_dir("47")
    out_path = artifacts / "FAQ.md"

    options = rightcode_options(
        cwd=root,
        project_dir=root,
        allowed_tools=None,
        permission_mode="bypass",
        interactive=True,
    )

    prompt = f"{PROMPT}\nWrite to: {out_path}"
    r = await console_run(prompt=prompt, options=options)

    print("Wrote FAQ:")
    print(str(out_path))
    print()
    print("Assistant final text:")
    print(r.final_text)


if __name__ == "__main__":
    asyncio.run(main())
