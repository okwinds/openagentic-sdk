# Clawdbot Parity v1 — Routing + Sessions + Mapping Store

## Analysis (Clawdbot)

Clawdbot resolves a route based on bindings/defaults:

- `(channel/account/peer/guild/team)` → `agentId + sessionKey`
- then loads workspace + session + model selection per agent

References:

- `src/routing/resolve-route.ts` (route rules + sessionKey + mainSessionKey)
- `src/auto-reply/reply/get-reply.ts` (agentId/sessionKey → workspace/session)

## Current State (openagentic-sdk)

SDK sessions are `session_id`-based and persisted by `FileSessionStore`:

- create new session (UUID-like hex)
- resume by passing `options.resume=<session_id>`

There is no built-in notion of “channel session key”.

## Design

Routing is Gateway-owned:

1) **ResolveRoute**: determine `agent_id` + deterministic `session_key` from envelope.
2) **SessionMap**: map `(agent_id, session_key)` to an AgentCore `session_id`.

### Session key scheme (v1)

Lowercase, stable, URL-safe:

- `session_key = f"{agent_id}:{channel}:{account_id}:{peer_kind}:{peer_id}"`

Optional:

- group keys: add `guild_id` / `team_id`
- “main session” per agent: `agent_id:main`

### Mapping store (v1)

SQLite (preferred) or JSON file:

Table `session_map`:

- `agent_id TEXT`
- `session_key TEXT PRIMARY KEY`
- `session_id TEXT` (AgentCore session id)
- `created_at REAL`
- `updated_at REAL`

## Plan (Implementation Outline)

1) Unit tests for `resolve_route(envelope)`.
2) Unit tests for `SessionMap.get_or_create(session_key)`:
   - stable mapping, durable across restarts
3) Integration test:
   - given two inbound messages in same dm, they resume same AgentCore session
4) Add gateway endpoint:
   - `POST /v1/chat/inbound` returns `outbound_payloads` and includes `session_id`

## TDD

Start with pure functions + sqlite-backed store tests using a temp directory.

## Acceptance Checklist

- Same peer goes to same session across restarts.
- Different peers do not share sessions unless configured.
- Mapping store is forward-compatible (migration-friendly).

