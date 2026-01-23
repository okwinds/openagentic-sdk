from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SkillDoc:
    name: str = ""
    summary: str = ""
    checklist: list[str] = field(default_factory=list)
    raw: str = ""


def parse_skill_markdown(text: str) -> SkillDoc:
    lines = text.splitlines()

    name = ""
    title_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# "):
            name = line[2:].strip()
            title_idx = i
            break

    # summary: first paragraph after title
    summary_lines: list[str] = []
    start = (title_idx + 1) if title_idx is not None else 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            break
        if line.lstrip().startswith("#"):
            break
        summary_lines.append(line.strip())
        i += 1
    summary = "\n".join(summary_lines).strip()

    # checklist: items under "## Checklist"
    checklist: list[str] = []
    checklist_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower() == "## checklist":
            checklist_idx = i + 1
            break
    if checklist_idx is not None:
        j = checklist_idx
        while j < len(lines):
            line = lines[j]
            stripped = line.strip()
            if stripped.startswith("## "):
                break
            if stripped.startswith("#"):
                break
            bullet = stripped.lstrip()
            if bullet.startswith("-") or bullet.startswith("*"):
                item = bullet[1:].strip()
                if item:
                    checklist.append(item)
            j += 1

    return SkillDoc(name=name, summary=summary, checklist=checklist, raw=text)

