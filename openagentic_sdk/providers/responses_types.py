from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class ResponsesConversationState:
    previous_response_id: str | None = None
    store: bool = True
    include: Sequence[str] = ()

