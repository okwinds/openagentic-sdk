from __future__ import annotations

import glob
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .options import OpenAgenticOptions
from .paths import default_session_root
from .project.claude import load_claude_project_settings


@dataclass(frozen=True, slots=True)
class InstructionDoc:
    label: str
    text: str


def _read_text_if_exists(p: Path) -> str | None:
    try:
        if not p.exists() or not p.is_file():
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return None


def _dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _resolve_instruction_globs(project_dir: Path, specs: Iterable[str]) -> list[Path]:
    out: list[Path] = []
    for raw in specs:
        spec = str(raw or "").strip()
        if not spec:
            continue
        if spec.startswith("file:"):
            spec = spec[len("file:") :].strip()
        # Always resolve relative specs against the project directory.
        base = str(project_dir / spec) if not Path(spec).is_absolute() else spec
        matches = glob.glob(base, recursive=True)
        for m in matches:
            p = Path(m)
            if p.exists() and p.is_file():
                out.append(p)
    # Deterministic ordering.
    return sorted(out, key=lambda p: str(p))


def build_system_prompt_text(options: OpenAgenticOptions) -> str | None:
    """Build the system prompt text fed to the model.

    This is intentionally a *single* string which the runtime injects as the first
    `system` message, keeping current provider integration simple.
    """

    parts: list[str] = []

    base = (options.system_prompt or "").strip()
    if base:
        parts.append(base)

    # Project-scoped instruction loading is opt-in.
    if "project" in set(options.setting_sources):
        project_dir = Path(options.project_dir or options.cwd)

        # OpenCode-style "rules" file.
        agents_paths: list[Path] = []
        global_root = options.session_root or default_session_root()
        agents_paths.append(Path(global_root) / "AGENTS.md")
        agents_paths.append(project_dir / "AGENTS.md")

        agents_texts: list[InstructionDoc] = []
        for p in agents_paths:
            txt = _read_text_if_exists(p)
            if txt and txt.strip():
                agents_texts.append(InstructionDoc(label=str(p), text=txt.strip()))

        for doc in agents_texts:
            parts.append("\n".join(["## Rules (AGENTS.md)", f"Source: {doc.label}", "", doc.text]).strip())

        # Claude Code compatibility: project memory + commands index.
        settings = load_claude_project_settings(str(project_dir))
        if settings.memory and settings.memory.strip():
            parts.append("\n".join(["## Project Memory (CLAUDE.md)", settings.memory.strip()]).strip())
        if settings.commands:
            lines = ["## Slash Commands"]
            for c in settings.commands:
                lines.append(f"- /{c.name} ({c.path})")
            parts.append("\n".join(lines).strip())

        # Additional instruction files (explicit opt-in via options).
        if options.instruction_files:
            resolved = _resolve_instruction_globs(project_dir, options.instruction_files)
            resolved_strs = _dedupe_keep_order([str(p) for p in resolved])
            for p_str in resolved_strs:
                p = Path(p_str)
                txt = _read_text_if_exists(p)
                if not txt or not txt.strip():
                    continue
                parts.append(
                    "\n".join(
                        [
                            "## Additional Instructions",
                            f"Source: {p.name}",
                            "",
                            txt.strip(),
                        ]
                    ).strip()
                )

    out = "\n\n".join([p for p in parts if p and p.strip()]).strip()
    return out or None
