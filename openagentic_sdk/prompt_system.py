from __future__ import annotations

import fnmatch
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .auth import OAuthAuth, all_auth
from .project.claude import load_claude_project_settings
from .opencode_config import load_merged_config
from .opencode_prompts import load_prompt_text
from .options import OpenAgenticOptions


@dataclass(frozen=True, slots=True)
class BuiltSystemPrompt:
    system_text: str
    instructions: str | None = None
    is_codex_session: bool = False


def _claude_project_blocks(*, project_dir: Path) -> list[str]:
    """Add OpenAgentic `.claude` compatibility blocks.

    OpenCode parity does not include these, but the SDK still promises `.claude`
    support in README when `setting_sources` includes "project".
    """

    blocks: list[str] = []
    settings = load_claude_project_settings(str(project_dir))
    if isinstance(settings.memory, str) and settings.memory.strip():
        blocks.append("Project memory from: " + str(project_dir / "CLAUDE.md") + "\n" + settings.memory)

    cmd_names = [c.name for c in settings.commands if isinstance(c.name, str) and c.name]
    # Also include OpenCode-style commands loaded from `opencode.json{c}` and
    # `.opencode/commands/**.md` directory packs.
    try:
        cfg = load_merged_config(cwd=str(project_dir))
    except Exception:  # noqa: BLE001
        cfg = {}
    if isinstance(cfg, dict):
        cmd_cfg = cfg.get("command") or cfg.get("commands")
        if isinstance(cmd_cfg, dict):
            for k in cmd_cfg.keys():
                if isinstance(k, str) and k:
                    cmd_names.append(k)
    if cmd_names:
        # Keep it short and predictable; the command templates themselves are loaded
        # via SlashCommand tool / `openagentic_sdk.commands.load_command_template`.
        rendered = "\n".join(f"/{n}" for n in sorted(set(cmd_names)))
        blocks.append("Available slash commands:\n" + rendered)
    return blocks


def _find_worktree_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / ".git").exists():
            return p
    return Path(cur.anchor or "/").resolve()


def _iter_up(start: Path, stop: Path) -> Iterable[Path]:
    cur = start.resolve()
    stop_r = stop.resolve()
    while True:
        yield cur
        if cur == stop_r:
            break
        if cur.parent == cur:
            break
        cur = cur.parent


def _find_up(filename: str, *, start: Path, stop: Path) -> list[Path]:
    out: list[Path] = []
    for d in _iter_up(start, stop):
        p = d / filename
        if p.exists() and p.is_file():
            out.append(p)
    return out


def _walk_files(cwd: Path) -> Iterable[Path]:
    # Deterministic: sort directories and files; follow symlinks.
    import os as _os

    for root, dirs, files in _os.walk(cwd, followlinks=True):
        dirs.sort()
        files.sort()
        for f in files:
            yield Path(root) / f


def _glob_in_dir(cwd: Path, pattern: str) -> list[Path]:
    """Glob like Bun.Glob(scan dot+symlink) relative to cwd."""

    pat = (pattern or "").strip()
    if not pat:
        return []
    out: list[Path] = []
    for p in _walk_files(cwd):
        try:
            rel = p.relative_to(cwd).as_posix()
        except Exception:  # noqa: BLE001
            continue
        if fnmatch.fnmatch(rel, pat):
            out.append(p)
    return out


def _glob_up(pattern: str, *, start: Path, stop: Path) -> list[Path]:
    out: list[Path] = []
    for d in _iter_up(start, stop):
        out.extend(_glob_in_dir(d, pattern))
    # Deterministic ordering.
    return sorted({p.resolve() for p in out}, key=lambda p: str(p))


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def _fetch_text(url: str, *, timeout_s: float) -> str:
    import urllib.request

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "openagentic-sdk", "Accept": "text/plain"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            if getattr(resp, "status", 200) >= 400:
                return ""
            raw = resp.read()
    except Exception:  # noqa: BLE001
        return ""
    return raw.decode("utf-8", errors="replace")


def _is_project_discovery_disabled() -> bool:
    v = os.environ.get("OPENCODE_DISABLE_PROJECT_CONFIG")
    if v is None:
        return False
    if v == "":
        return True
    return v.strip().lower() not in {"0", "false", "no", "off"}


def _global_config_dir() -> Path:
    # XDG config dir is the OpenCode global root.
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser().resolve() / "opencode"
    home = Path(os.environ.get("OPENCODE_TEST_HOME") or Path.home()).expanduser().resolve()
    return home / ".config" / "opencode"


def _opencode_provider_prompt(model_id: str) -> str:
    mid = (model_id or "").lower()
    if "gpt-5" in mid:
        return load_prompt_text("codex_header.txt")
    if "gpt-" in mid or "o1" in mid or "o3" in mid:
        return load_prompt_text("beast.txt")
    if "gemini-" in mid:
        return load_prompt_text("gemini.txt")
    if "claude" in mid:
        return load_prompt_text("anthropic.txt")
    return load_prompt_text("qwen.txt")


def _opencode_header(provider_id: str) -> list[str]:
    if "anthropic" in (provider_id or "").lower():
        return [load_prompt_text("anthropic_spoof.txt").strip()]
    return []


def _opencode_environment_block(*, cwd: str) -> str:
    p = Path(cwd).resolve()
    worktree = _find_worktree_root(p)
    is_git = (worktree / ".git").exists()
    today = date.today().strftime("%a %b %d %Y")
    return "\n".join(
        [
            "Here is some useful information about the environment you are running in:",
            "<env>",
            f"  Working directory: {p}",
            f"  Is directory a git repo: {'yes' if is_git else 'no'}",
            # Match Node's `process.platform` string values (linux/darwin/win32).
            f"  Platform: {sys.platform}",
            f"  Today's date: {today}",
            "</env>",
            "<files>",
            "",
            "</files>",
        ]
    )


def _resolve_relative_instruction(instruction: str, *, instance_dir: Path, worktree: Path) -> list[Path]:
    if not _is_project_discovery_disabled():
        return _glob_up(instruction, start=instance_dir, stop=worktree)

    cfg_dir = os.environ.get("OPENCODE_CONFIG_DIR")
    if not cfg_dir:
        return []
    d = Path(cfg_dir).expanduser().resolve()
    return _glob_up(instruction, start=d, stop=d)


def _custom_instruction_blocks(*, options: OpenAgenticOptions, instance_dir: Path, worktree: Path) -> list[str]:
    cfg = {}
    try:
        cfg = load_merged_config(cwd=str(instance_dir))
    except Exception:  # noqa: BLE001
        cfg = {}

    paths: list[str] = []

    # Local rules (only when project discovery is enabled).
    if not _is_project_discovery_disabled():
        for rule_file in ("AGENTS.md", "CLAUDE.md", "CONTEXT.md"):
            matches = _find_up(rule_file, start=instance_dir, stop=worktree)
            if matches:
                for p in matches:
                    sp = str(p)
                    if sp not in paths:
                        paths.append(sp)
                break

    # Global rules (first existing only).
    global_candidates: list[Path] = []
    global_candidates.append(_global_config_dir() / "AGENTS.md")

    if not os.environ.get("OPENCODE_DISABLE_CLAUDE_CODE_PROMPT"):
        global_candidates.append(Path(os.environ.get("OPENCODE_TEST_HOME") or Path.home()).expanduser().resolve() / ".claude" / "CLAUDE.md")

    cfg_dir = os.environ.get("OPENCODE_CONFIG_DIR")
    if cfg_dir:
        global_candidates.append(Path(cfg_dir).expanduser().resolve() / "AGENTS.md")

    for p in global_candidates:
        if p.exists() and p.is_file():
            sp = str(p)
            if sp not in paths:
                paths.append(sp)
            break

    urls: list[str] = []

    # OpenAgentic: programmatic instruction_files.
    # Resolve patterns relative to project_dir/cwd and include matching files.
    for pat in getattr(options, "instruction_files", ()) or ():
        if not isinstance(pat, str) or not pat.strip():
            continue
        base = Path(options.project_dir or options.cwd).expanduser().resolve()
        for m in _glob_in_dir(base, pat.strip()):
            sp = str(m)
            if sp not in paths:
                paths.append(sp)
    instructions = cfg.get("instructions") if isinstance(cfg, dict) else None
    if isinstance(instructions, list):
        for ins in instructions:
            if not isinstance(ins, str) or not ins.strip():
                continue
            instruction = ins.strip()
            if instruction.startswith("http://") or instruction.startswith("https://"):
                urls.append(instruction)
                continue
            if instruction.startswith("~/"):
                home = Path(os.environ.get("OPENCODE_TEST_HOME") or Path.home()).expanduser().resolve()
                instruction = str(home / instruction[2:])
            if Path(instruction).is_absolute():
                ip = Path(instruction)
                matches = _glob_in_dir(ip.parent, ip.name)
            else:
                matches = _resolve_relative_instruction(instruction, instance_dir=instance_dir, worktree=worktree)
            for m in matches:
                sp = str(m)
                if sp not in paths:
                    paths.append(sp)

    blocks: list[str] = []
    for p_str in paths:
        txt = _read_text(Path(p_str))
        blocks.append("Instructions from: " + p_str + "\n" + txt)

    # URL instructions are only included when fetch returns non-empty.
    for u in urls:
        txt = _fetch_text(u, timeout_s=5.0)
        if txt:
            blocks.append("Instructions from: " + u + "\n" + txt)

    # Hook point: options.hooks may want to transform system prompts. Not parity yet.
    _ = options
    return blocks


def build_system_prompt(options: OpenAgenticOptions) -> BuiltSystemPrompt:
    # Parity behavior is opt-in for now: only activate when the caller includes
    # "project" in setting_sources (same as previous behavior).
    if "project" not in set(options.setting_sources):
        base = (options.system_prompt or "").strip()
        return BuiltSystemPrompt(system_text=base)

    instance_dir = Path(options.cwd).resolve()
    worktree = _find_worktree_root(instance_dir)

    # Codex session detection (OpenCode: openai + oauth). We approximate using
    # auth store entry for provider_id "openai".
    provider_id = getattr(options.provider, "name", "") or ""
    auth = all_auth().get("openai")
    is_codex = provider_id.startswith("openai") and isinstance(auth, OAuthAuth)

    system_blocks: list[str] = []
    system_blocks.extend(_opencode_header(provider_id))

    # Base provider prompt: skipped for Codex session.
    if not is_codex:
        system_blocks.append(_opencode_provider_prompt(options.model).strip())

    # Environment + custom instructions.
    system_blocks.append(_opencode_environment_block(cwd=options.cwd))
    system_blocks.extend(_custom_instruction_blocks(options=options, instance_dir=instance_dir, worktree=worktree))

    # OpenAgentic `.claude` compatibility blocks are intentionally NOT part of
    # OpenCode parity. Gate them behind an explicit setting source.
    if "claude" in set(options.setting_sources):
        try:
            project_root = Path(options.project_dir or options.cwd).expanduser().resolve()
            system_blocks.extend(_claude_project_blocks(project_dir=project_root))
        except Exception:  # noqa: BLE001
            pass

    # Programmatic system prompt injection should have highest precedence.
    if isinstance(options.system_prompt, str) and options.system_prompt.strip():
        system_blocks.append(options.system_prompt.strip())

    system_text = "\n\n".join([b for b in system_blocks if b is not None and str(b).strip()]).strip()

    instructions: str | None = None
    if is_codex:
        instructions = load_prompt_text("codex_header.txt").strip()

    return BuiltSystemPrompt(system_text=system_text, instructions=instructions, is_codex_session=is_codex)


def build_system_prompt_text(options: OpenAgenticOptions) -> str | None:
    built = build_system_prompt(options)
    return built.system_text or None
