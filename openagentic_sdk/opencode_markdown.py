from __future__ import annotations

import re


# Keep these regexes byte-for-byte aligned with OpenCode's ConfigMarkdown.
#
# Source of truth:
# - /mnt/e/development/opencode/packages/opencode/src/config/markdown.ts

FILE_REGEX = re.compile(r"(?<![\w`])@(\.?[^\s`,.]*(?:\.[^\s`,.]+)*)")
SHELL_REGEX = re.compile(r"!`([^`]+)`")


def files(template: str) -> list[str]:
    """Extract OpenCode-style @file references in appearance order."""

    if not isinstance(template, str) or not template:
        return []
    return [m.group(1) for m in FILE_REGEX.finditer(template) if m.group(1)]


def shell(template: str) -> list[str]:
    """Extract OpenCode-style !`cmd` snippets in appearance order."""

    if not isinstance(template, str) or not template:
        return []
    return [m.group(1) for m in SHELL_REGEX.finditer(template) if m.group(1)]
