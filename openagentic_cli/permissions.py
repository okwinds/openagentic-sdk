from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from openagentic_sdk.permissions.gate import PermissionGate

PromptFn = Callable[[str], bool]


_SAFE_TOOLS: set[str] = {
    "Read",
    "Glob",
    "Grep",
    "Skill",
    "SlashCommand",
    "TodoWrite",
    "AskUserQuestion",
}

_AUTO_TOOLS: set[str] = {
    "Write",
    "Edit",
    "Bash",
    "NotebookEdit",
}


_DANGEROUS_DELETE_RE: list[re.Pattern[str]] = [
    re.compile(r"(^|[;&|()\s])rm(\s|$)", re.IGNORECASE),
    re.compile(r"(^|[;&|()\s])rmdir(\s|$)", re.IGNORECASE),
    re.compile(r"(^|[;&|()\s])rd(\s|$)", re.IGNORECASE),
    re.compile(r"(^|[;&|()\s])del(\s|$)", re.IGNORECASE),
    re.compile(r"(^|[;&|()\s])erase(\s|$)", re.IGNORECASE),
    re.compile(r"\bremove-item\b", re.IGNORECASE),
    re.compile(r"\brimraf\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\b", re.IGNORECASE),
]


def is_dangerous_delete_command(command: str) -> bool:
    s = command or ""
    return any(rx.search(s) for rx in _DANGEROUS_DELETE_RE)


def _resolve_best_effort(p: Path) -> Path:
    try:
        return p.resolve(strict=False)
    except Exception:
        return Path(os.path.abspath(os.fspath(p)))


def _in_tree(path: Path, root: Path) -> bool:
    a = _resolve_best_effort(path)
    b = _resolve_best_effort(root)
    try:
        return a.is_relative_to(b)  # py3.9+
    except AttributeError:  # pragma: no cover
        ap = os.path.normcase(os.fspath(a))
        bp = os.path.normcase(os.fspath(b))
        return os.path.commonpath([ap, bp]) == bp
    except ValueError:
        return False


def _tool_path(tool_name: str, tool_input: Mapping[str, Any], *, cwd: Path) -> Path | None:
    if tool_name in ("Write", "Edit", "NotebookEdit"):
        raw = tool_input.get("file_path", tool_input.get("filePath"))
        if not isinstance(raw, str) or not raw.strip():
            return None
        p = Path(raw.strip())
        return p if p.is_absolute() else (cwd / p)
    if tool_name == "Bash":
        raw = tool_input.get("workdir")
        if raw is None:
            return cwd
        if not isinstance(raw, str) or not raw.strip():
            return cwd
        p = Path(raw.strip())
        return p if p.is_absolute() else (cwd / p)
    return None


def _format_tool_prompt(tool_name: str, tool_input: Mapping[str, Any]) -> str:
    if tool_name == "Bash":
        cmd = tool_input.get("command")
        extra = f" command={cmd!r}" if isinstance(cmd, str) and cmd else ""
        return f"Allow tool {tool_name}?{extra} [y/N] "
    if tool_name in ("Write", "Edit", "NotebookEdit"):
        p = tool_input.get("file_path", tool_input.get("filePath"))
        extra = f" file={p!r}" if isinstance(p, str) and p else ""
        return f"Allow tool {tool_name}?{extra} [y/N] "
    return f"Allow tool {tool_name}? [y/N] "


@dataclass
class CliPermissionPolicy:
    cwd: Path
    auto_root: Path
    auto_allow_dangerous: bool
    prompt_fn: PromptFn

    def allow(self, tool_name: str, tool_input: Mapping[str, Any]) -> bool:
        if tool_name in _SAFE_TOOLS:
            return True

        if tool_name == "Bash":
            cmd = tool_input.get("command")
            if isinstance(cmd, str) and cmd and is_dangerous_delete_command(cmd):
                return bool(self.prompt_fn(_format_tool_prompt(tool_name, tool_input)))

        if tool_name in _AUTO_TOOLS and self.auto_allow_dangerous:
            p = _tool_path(tool_name, tool_input, cwd=self.cwd)
            if p is not None and _in_tree(p, self.auto_root):
                return True

        return bool(self.prompt_fn(_format_tool_prompt(tool_name, tool_input)))

    async def approver(self, tool_name: str, tool_input: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
        _ = context
        return self.allow(tool_name, tool_input)


def build_permission_gate(policy: CliPermissionPolicy) -> PermissionGate:
    return PermissionGate(permission_mode="callback", approver=policy.approver)
