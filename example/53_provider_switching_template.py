from __future__ import annotations

import asyncio
import os

from _common import repo_root, rightcode_options
from openagentic_sdk.console import console_run
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions import PermissionGate
from openagentic_sdk.providers.openai import OpenAIProvider


PROMPT = """\
Provider switching template.

This example demonstrates how to keep your application logic constant while
swapping providers via an env var.

- OA_PROVIDER=rightcode (default): OpenAI-compatible backend via RIGHTCODE_* env
- OA_PROVIDER=openai: OpenAI API via OPENAI_API_KEY

Task: Explain how tool calls and session persistence work in this SDK.
"""


def build_options() -> OpenAgenticOptions:
    provider_kind = os.environ.get("OA_PROVIDER", "rightcode").strip().lower()

    if provider_kind == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("Missing required env var: OPENAI_API_KEY")

        # Use the default OpenAI provider. This path is useful when you want to
        # test against api.openai.com rather than an OpenAI-compatible gateway.
        model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
        root = repo_root()
        return OpenAgenticOptions(
            provider=OpenAIProvider(),
            model=model,
            api_key=api_key,
            cwd=str(root),
            project_dir=str(root),
            session_root=None,
            allowed_tools=None,
            permission_gate=PermissionGate(permission_mode="prompt", interactive=True),
            setting_sources=["project"],
        )

    # Default: RIGHTCODE-backed options (Responses provider internally).
    return rightcode_options(
        cwd=repo_root(),
        project_dir=repo_root(),
        allowed_tools=None,
        permission_mode="prompt",
        interactive=True,
    )


async def main() -> None:
    options = build_options()
    r = await console_run(prompt=PROMPT, options=options)
    print(r.final_text)


if __name__ == "__main__":
    asyncio.run(main())
