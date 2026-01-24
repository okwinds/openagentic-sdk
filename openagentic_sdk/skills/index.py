from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..paths import default_session_root
from .parse import parse_skill_markdown


@dataclass(frozen=True, slots=True)
class SkillInfo:
    name: str
    description: str
    summary: str
    path: str


def _iter_skill_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for dirname in ("skill", "skills"):
        d = root / dirname
        if not d.exists():
            continue
        out.extend([p for p in d.glob("**/SKILL.md") if p.is_file()])
    return out


def index_skills(*, project_dir: str) -> list[SkillInfo]:
    project_root = Path(project_dir)
    global_root = default_session_root()
    claude_root = project_root / ".claude"

    # Precedence: project skills override global skills when name collides.
    seen: dict[str, SkillInfo] = {}
    for root in (global_root, claude_root):
        for p in _iter_skill_files(root):
            raw = p.read_text(encoding="utf-8", errors="replace")
            doc = parse_skill_markdown(raw)
            name = doc.name or p.parent.name
            if not name:
                continue
            seen[name] = SkillInfo(name=name, description=doc.description, summary=doc.summary, path=str(p))

    return sorted(seen.values(), key=lambda s: s.name)
