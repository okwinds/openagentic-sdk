from __future__ import annotations

from typing import Any, Mapping

from ...reply.envelope import InboundEnvelope


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return str(int(v)) if isinstance(v, int) else str(v)
    return str(v)


def normalize_telegram_update(update: Mapping[str, Any], *, account_id: str) -> InboundEnvelope:
    msg = update.get("message") if isinstance(update, dict) else None
    if not isinstance(msg, dict):
        msg = update.get("edited_message") if isinstance(update, dict) else None
    msg = msg if isinstance(msg, dict) else {}

    chat = msg.get("chat")
    chat = chat if isinstance(chat, dict) else {}
    chat_id = _as_str(chat.get("id")).strip()
    chat_type = _as_str(chat.get("type")).strip().lower()

    peer_kind = "dm" if chat_type in {"private", "dm"} else "group"
    text = _as_str(msg.get("text")).strip()

    return InboundEnvelope(
        channel="telegram",
        account_id=_as_str(account_id).strip(),
        peer_kind=peer_kind,
        peer_id=chat_id,
        text=text,
    )

