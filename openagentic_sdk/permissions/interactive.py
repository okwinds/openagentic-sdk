from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class InteractiveApprover:
    input_fn: Callable[[str], str]

    def ask_yes_no(self, prompt: str) -> bool:
        ans = str(self.input_fn(prompt)).strip().lower()
        return ans in ("y", "yes")

