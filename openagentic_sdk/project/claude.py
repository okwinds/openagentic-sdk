from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True, slots=True)
class ClaudeSkillInfo:
    name: str
    path: str


@dataclass(frozen=True, slots=True)
class ClaudeCommandInfo:
    name: str
    path: str


@dataclass(frozen=True, slots=True)
class ClaudeProjectSettings:
    project_dir: str
    memory: str | None
    skills: list[ClaudeSkillInfo]
    commands: list[ClaudeCommandInfo]


def load_claude_project_settings(project_dir: str) -> ClaudeProjectSettings:
    root = Path(project_dir)
    memory = None
    if (root / "CLAUDE.md").exists():
        memory = (root / "CLAUDE.md").read_text(encoding="utf-8", errors="replace")
    elif (root / ".claude" / "CLAUDE.md").exists():
        memory = (root / ".claude" / "CLAUDE.md").read_text(encoding="utf-8", errors="replace")

    skills: list[ClaudeSkillInfo] = []
    skills_root = root / ".claude" / "skills"
    if skills_root.exists():
        for p in skills_root.glob("**/SKILL.md"):
            # Use the containing folder name as the skill name by default.
            name = p.parent.name
            skills.append(ClaudeSkillInfo(name=name, path=str(p)))

    commands: list[ClaudeCommandInfo] = []
    cmd_root = root / ".claude" / "commands"
    if cmd_root.exists():
        for p in sorted(cmd_root.glob("*.md")):
            commands.append(ClaudeCommandInfo(name=p.stem, path=str(p)))

    return ClaudeProjectSettings(project_dir=str(root), memory=memory, skills=sorted(skills, key=lambda s: s.name), commands=commands)

