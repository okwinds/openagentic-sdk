from __future__ import annotations

from importlib import resources


def load_command_text(name: str) -> str:
    """Load an embedded OpenCode built-in command template."""

    fname = {
        "init": "initialize.txt",
        "review": "review.txt",
    }.get(name)
    if not fname:
        raise KeyError(name)
    return resources.files(__package__).joinpath(fname).read_text(encoding="utf-8")
