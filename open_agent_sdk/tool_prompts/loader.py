from __future__ import annotations

import datetime as _dt
import re
from functools import lru_cache
from typing import Any, Mapping

try:
    from importlib import resources as _resources
except Exception:  # pragma: no cover
    _resources = None  # type: ignore[assignment]


_DOLLAR_RE = re.compile(r"\$\{([A-Za-z0-9_]+)\}")
_BRACE_RE = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")


@lru_cache(maxsize=128)
def _read_text(filename: str) -> str:
    if _resources is not None:
        try:
            return _resources.files(__package__).joinpath(filename).read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    # Fallback for dev environments where package data isn't installed.
    from pathlib import Path

    p = Path(__file__).with_name(filename)
    return p.read_text(encoding="utf-8", errors="replace")


def _substitute(text: str, variables: Mapping[str, Any]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key in variables:
            return str(variables[key])
        return m.group(0)

    text = _DOLLAR_RE.sub(repl, text)
    text = _BRACE_RE.sub(repl, text)
    return text


def render_tool_prompt(template_name: str, *, variables: Mapping[str, Any] | None = None) -> str:
    vars2: dict[str, Any] = {"date": _dt.date.today().isoformat()}
    if variables:
        vars2.update(dict(variables))
    raw = _read_text(f"{template_name}.txt")
    return _substitute(raw, vars2).strip()

