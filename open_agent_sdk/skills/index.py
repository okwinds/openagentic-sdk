from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .parse import parse_skill_markdown


@dataclass(frozen=True, slots=True)
class SkillInfo:
    name: str
    summary: str
    path: str


def index_skills(*, project_dir: str) -> list[SkillInfo]:
    root = Path(project_dir)
    skills_root = root / ".claude" / "skills"
    if not skills_root.exists():
        return []
    out: list[SkillInfo] = []
    for p in skills_root.glob("**/SKILL.md"):
        raw = p.read_text(encoding="utf-8", errors="replace")
        doc = parse_skill_markdown(raw)
        name = doc.name or p.parent.name
        out.append(SkillInfo(name=name, summary=doc.summary, path=str(p)))
    return sorted(out, key=lambda s: s.name)

