from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SkillDoc:
    name: str = ""
    description: str = ""
    summary: str = ""
    checklist: list[str] = field(default_factory=list)
    raw: str = ""


def _parse_frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    """
    Very small YAML-ish frontmatter parser:
    - Only supports top-of-file '---' ... '---'
    - Only supports 'key: value' single-line pairs
    Returns (meta, content_start_index).
    """
    if not lines or lines[0].strip() != "---":
        return {}, 0
    meta: dict[str, str] = {}
    i = 1
    while i < len(lines):
        line = lines[i].rstrip("\n")
        if line.strip() == "---":
            return meta, i + 1
        if ":" in line:
            k, v = line.split(":", 1)
            key = k.strip()
            val = v.strip().strip("'").strip('"')
            if key and val:
                meta[key] = val
        i += 1
    return meta, 0


def strip_frontmatter(text: str) -> str:
    """
    Remove top-of-file '---' frontmatter block if present.
    """
    lines = text.splitlines()
    _, start = _parse_frontmatter(lines)
    if start <= 0:
        return text
    return "\n".join(lines[start:]) + ("\n" if text.endswith("\n") else "")


def parse_skill_markdown(text: str) -> SkillDoc:
    lines = text.splitlines()
    meta, _ = _parse_frontmatter(lines)

    name = ""
    title_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# "):
            name = line[2:].strip()
            title_idx = i
            break
    # Prefer canonical id from frontmatter (e.g. name: main-process).
    fm_name = meta.get("name") or ""
    if fm_name:
        name = fm_name

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

    return SkillDoc(
        name=name,
        description=meta.get("description") or "",
        summary=summary,
        checklist=checklist,
        raw=text,
    )
