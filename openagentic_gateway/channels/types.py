from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ChannelMeta:
    id: str
    label: str | None = None
    aliases: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ChannelCapabilities:
    supports_webhooks: bool = False
    supports_streaming: bool = False


@dataclass(frozen=True, slots=True)
class ChannelAccountSnapshot:
    account_id: str
    running: bool = False
    last_error: str | None = None
    last_start_at: float | None = None
    last_stop_at: float | None = None
