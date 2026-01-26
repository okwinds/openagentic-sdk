from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .opencode_config import load_merged_config
from .opencode_commands import load_command_text


def _find_worktree_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / ".git").exists():
            return p
    return Path(cur.anchor or "/").resolve()


@dataclass(frozen=True, slots=True)
class CommandTemplate:
    name: str
    source: str
    content: str
    description: str | None = None
    agent: str | None = None
    model: str | None = None
    subtask: bool | None = None


def _default_global_opencode_config_dir() -> Path:
    return Path(os.environ.get("OPENCODE_CONFIG_DIR") or (Path.home() / ".config" / "opencode")).expanduser()


def load_command_template(*, name: str, project_dir: str) -> CommandTemplate | None:
    """Load a command template by name.

    Precedence (high -> low):
    - config-defined command template (opencode.json/opencode.jsonc merged)
    - project `.opencode/commands/<name>.md`
    - project `.claude/commands/<name>.md` (compat)
    - global `~/.config/opencode/commands/<name>.md`
    """

    if not name:
        return None
    base = Path(project_dir)

    # Config-defined commands.
    try:
        cfg = load_merged_config(cwd=str(base))
    except Exception:
        cfg = {}
    if isinstance(cfg, dict):
        cmd_cfg = cfg.get("command") or cfg.get("commands")
        if isinstance(cmd_cfg, dict):
            entry = cmd_cfg.get(name)
            if isinstance(entry, dict):
                tpl = entry.get("template") or entry.get("prompt") or entry.get("content")
                if isinstance(tpl, str) and tpl.strip():
                    return CommandTemplate(
                        name=name,
                        source=f"config:{name}",
                        content=tpl.strip(),
                        description=entry.get("description") if isinstance(entry.get("description"), str) else None,
                        agent=entry.get("agent") if isinstance(entry.get("agent"), str) else None,
                        model=entry.get("model") if isinstance(entry.get("model"), str) else None,
                        subtask=entry.get("subtask") if isinstance(entry.get("subtask"), bool) else None,
                    )
            if isinstance(entry, str) and entry.strip():
                return CommandTemplate(name=name, source=f"config:{name}", content=entry.strip())

    # On-disk commands.
    candidates: list[Path] = [
        base / ".opencode" / "commands" / f"{name}.md",
        base / ".claude" / "commands" / f"{name}.md",
    ]
    global_root = _default_global_opencode_config_dir()
    candidates.append(global_root / "commands" / f"{name}.md")

    for p in candidates:
        if p.exists() and p.is_file():
            return CommandTemplate(
                name=name,
                source=str(p),
                content=p.read_text(encoding="utf-8", errors="replace"),
            )

    # Built-in OpenCode commands (lowest precedence).
    if name in ("init", "review"):
        try:
            txt = load_command_text(name)
            worktree = _find_worktree_root(base)
            txt = txt.replace("${path}", str(worktree))
            return CommandTemplate(name=name, source=f"builtin:{name}", content=txt)
        except Exception:
            return None
    return None
