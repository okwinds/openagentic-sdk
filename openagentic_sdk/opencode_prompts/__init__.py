from __future__ import annotations

from functools import lru_cache
from importlib.resources import files


@lru_cache(maxsize=64)
def load_prompt_text(name: str) -> str:
    """Load an embedded OpenCode prompt template by filename.

    Files are stored under this package so the SDK is self-contained.
    """

    p = files(__package__).joinpath(name)
    return p.read_text(encoding="utf-8", errors="replace")
