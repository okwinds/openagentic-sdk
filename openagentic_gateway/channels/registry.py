from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


@dataclass(frozen=True, slots=True)
class ChannelRegistryEntry:
    plugin: Any

    @property
    def id(self) -> str:
        return str(getattr(self.plugin, "id", "") or "").strip()

    @property
    def aliases(self) -> list[str]:
        meta = getattr(self.plugin, "meta", None)
        aliases = getattr(meta, "aliases", None)
        if isinstance(aliases, list):
            return [str(a) for a in aliases if isinstance(a, str) and a.strip()]
        return []


class ChannelRegistry:
    def __init__(self) -> None:
        self._entries: list[ChannelRegistryEntry] = []

    def register(self, plugin: Any) -> None:
        self._entries.append(ChannelRegistryEntry(plugin=plugin))

    def list_plugins(self) -> list[Any]:
        return [e.plugin for e in self._entries]

    def get(self, raw: str) -> Any | None:
        key = _norm(raw)
        if not key:
            return None
        for e in self._entries:
            pid = _norm(e.id)
            if pid and pid == key:
                return e.plugin
            for a in e.aliases:
                if _norm(a) == key:
                    return e.plugin
        return None

