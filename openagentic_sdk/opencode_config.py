from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


_ENV_RE = re.compile(r"\{env:([A-Za-z_][A-Za-z0-9_]*)\}")
_FILE_RE = re.compile(r"\{file:([^}]+)\}")


def _strip_jsonc_comments(text: str) -> str:
    """Strip // and /* */ comments while preserving strings."""

    out: list[str] = []
    i = 0
    n = len(text)
    in_str = False
    str_quote = ""
    esc = False
    in_line_comment = False
    in_block_comment = False

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                out.append(ch)
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == str_quote:
                in_str = False
                str_quote = ""
            i += 1
            continue

        # Not in string/comment.
        if ch in ('"', "'"):
            in_str = True
            str_quote = ch
            out.append(ch)
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] (outside strings)."""

    out: list[str] = []
    i = 0
    n = len(text)
    in_str = False
    str_quote = ""
    esc = False

    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == str_quote:
                in_str = False
                str_quote = ""
            i += 1
            continue

        if ch in ('"', "'"):
            in_str = True
            str_quote = ch
            out.append(ch)
            i += 1
            continue

        if ch == ",":
            # Look ahead for the next non-ws character.
            j = i + 1
            while j < n and text[j] in (" ", "\t", "\r", "\n"):
                j += 1
            if j < n and text[j] in ("}", "]"):
                i += 1
                continue

        out.append(ch)
        i += 1

    return "".join(out)


def _deep_merge(a: Any, b: Any) -> Any:
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            if k in out:
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = v
        return out

    if isinstance(a, list) and isinstance(b, list):
        # Merge lists with dedupe for scalars.
        out: list[Any] = []
        seen: set[str] = set()
        for item in [*a, *b]:
            if isinstance(item, (str, int, float, bool)) or item is None:
                key = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if key in seen:
                    continue
                seen.add(key)
            out.append(item)
        return out

    return b


def _substitute_in_str(s: str, *, base_dir: Path) -> str:
    def env_repl(m: re.Match[str]) -> str:
        return os.environ.get(m.group(1), "")

    def file_repl(m: re.Match[str]) -> str:
        raw = m.group(1).strip()
        p = Path(raw)
        if not p.is_absolute():
            p = base_dir / p
        try:
            return p.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:  # noqa: BLE001
            return ""

    s2 = _ENV_RE.sub(env_repl, s)
    s3 = _FILE_RE.sub(file_repl, s2)
    return s3


def _substitute(obj: Any, *, base_dir: Path) -> Any:
    if isinstance(obj, str):
        return _substitute_in_str(obj, base_dir=base_dir)
    if isinstance(obj, list):
        return [_substitute(x, base_dir=base_dir) for x in obj]
    if isinstance(obj, dict):
        return {k: _substitute(v, base_dir=base_dir) for k, v in obj.items()}
    return obj


def load_config_file(path: str) -> dict[str, Any]:
    p = Path(path)
    raw = p.read_text(encoding="utf-8", errors="replace")
    cleaned = _strip_trailing_commas(_strip_jsonc_comments(raw))
    obj = json.loads(cleaned) if cleaned.strip() else {}
    if not isinstance(obj, dict):
        raise ValueError("config must be a JSON object")
    return _substitute(obj, base_dir=p.parent)


def _iter_parent_dirs(start: Path) -> Iterable[Path]:
    cur = start
    while True:
        yield cur
        if cur.parent == cur:
            break
        cur = cur.parent


def _discover_config_paths(cwd: Path) -> list[Path]:
    """Return config file candidates in increasing precedence order."""

    names = ["opencode.json", "opencode.jsonc"]
    found: list[Path] = []
    for d in reversed(list(_iter_parent_dirs(cwd))):
        for name in names:
            p = d / name
            if p.exists() and p.is_file():
                found.append(p)
        # .opencode overrides project config at that directory.
        dot = d / ".opencode"
        for name in names:
            p = dot / name
            if p.exists() and p.is_file():
                found.append(p)
    return found


def load_merged_config(*, cwd: str, global_config_dir: str | None = None) -> dict[str, Any]:
    cwd_p = Path(cwd)

    merged: dict[str, Any] = {}

    # Global config root (lowest precedence).
    global_root: Path | None = None
    if global_config_dir:
        global_root = Path(global_config_dir)
    else:
        # OpenCode-compatible default.
        global_root = Path(os.environ.get("OPENCODE_CONFIG_DIR") or Path.home() / ".config" / "opencode")

    if global_root.exists():
        for name in ("opencode.json", "opencode.jsonc"):
            p = global_root / name
            if p.exists() and p.is_file():
                merged = _deep_merge(merged, load_config_file(str(p)))

    for p in _discover_config_paths(cwd_p):
        merged = _deep_merge(merged, load_config_file(str(p)))

    return merged
