from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InboundEnvelope:
    channel: str
    account_id: str
    peer_kind: str
    peer_id: str
    text: str


@dataclass(frozen=True, slots=True)
class OutboundPayload:
    kind: str
    text: str


def render_prompt(env: InboundEnvelope) -> str:
    channel = (env.channel or "").strip()
    account_id = (env.account_id or "").strip()
    peer_kind = (env.peer_kind or "").strip()
    peer_id = (env.peer_id or "").strip()
    header = f"[channel={channel} account={account_id} peer={peer_kind}:{peer_id}]".strip()
    body = (env.text or "").strip()
    if not body:
        return header
    return f"{header}\n\n{body}"

