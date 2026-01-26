from __future__ import annotations

from dataclasses import dataclass


def _norm(s: str) -> str:
    return (s or "").strip().lower()


@dataclass(frozen=True, slots=True)
class ResolvedRoute:
    agent_id: str
    session_key: str


def build_session_key(
    *,
    agent_id: str,
    channel: str,
    account_id: str,
    peer_kind: str,
    peer_id: str,
) -> str:
    # v1 deterministic, URL-safe-ish key. Future expansions can add guild/team.
    parts = [
        _norm(agent_id),
        _norm(channel),
        _norm(account_id),
        _norm(peer_kind),
        _norm(peer_id),
    ]
    return ":".join([p for p in parts if p])


def resolve_route(
    *,
    agent_id: str,
    channel: str,
    account_id: str,
    peer_kind: str,
    peer_id: str,
) -> ResolvedRoute:
    key = build_session_key(
        agent_id=agent_id,
        channel=channel,
        account_id=account_id,
        peer_kind=peer_kind,
        peer_id=peer_id,
    )
    return ResolvedRoute(agent_id=_norm(agent_id), session_key=key)

