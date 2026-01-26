from __future__ import annotations

from dataclasses import dataclass, replace

from openagentic_sdk.api import run as sdk_run
from openagentic_sdk.options import OpenAgenticOptions

from ..routing.resolve_route import resolve_route
from ..sessions.session_map import SessionMap
from .envelope import InboundEnvelope, OutboundPayload, render_prompt


@dataclass(frozen=True, slots=True)
class ReplyResult:
    session_id: str
    payloads: list[OutboundPayload]


class ReplyEngine:
    def __init__(self, *, options: OpenAgenticOptions, session_map: SessionMap, agent_id: str) -> None:
        self._options = options
        self._session_map = session_map
        self._agent_id = agent_id

    async def get_reply(self, env: InboundEnvelope) -> ReplyResult:
        route = resolve_route(
            agent_id=self._agent_id,
            channel=env.channel,
            account_id=env.account_id,
            peer_kind=env.peer_kind,
            peer_id=env.peer_id,
        )
        session_id = self._session_map.get_or_create(agent_id=route.agent_id, session_key=route.session_key)
        prompt = render_prompt(env)

        opts2 = replace(self._options, resume=session_id)
        res = await sdk_run(prompt=prompt, options=opts2)
        text = (res.final_text or "").strip()
        payloads = [OutboundPayload(kind="send_text", text=text)]
        return ReplyResult(session_id=session_id, payloads=payloads)

