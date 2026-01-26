#!/usr/bin/env python3
from __future__ import annotations

import sys
import zipfile
from pathlib import Path


REQUIRED_PREFIXES = (
    "openagentic_sdk/opencode_prompts/",
    "openagentic_sdk/opencode_commands/",
    "openagentic_sdk/tool_prompts/",
    "openagentic_sdk/js_runner/",
)

REQUIRED_FILES = (
    "openagentic_sdk/opencode_prompts/codex_header.txt",
    "openagentic_sdk/opencode_commands/initialize.txt",
    "openagentic_sdk/tool_prompts/bash.txt",
    "openagentic_sdk/js_runner/opencode_tool_runner.mjs",
)


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in {"-h", "--help"}:
        print("usage: check_wheel_data.py path/to/package.whl")
        return 2

    wheel_path = Path(argv[1])
    if not wheel_path.exists():
        print(f"error: wheel not found: {wheel_path}")
        return 2

    with zipfile.ZipFile(wheel_path) as zf:
        names = set(zf.namelist())

    missing_files = [p for p in REQUIRED_FILES if p not in names]
    missing_prefixes = [p for p in REQUIRED_PREFIXES if not any(n.startswith(p) for n in names)]

    if missing_files or missing_prefixes:
        print("wheel is missing required package data:")
        for p in missing_prefixes:
            print(f"- missing any files under: {p}")
        for p in missing_files:
            print(f"- missing file: {p}")
        return 1

    print("wheel package data looks OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

