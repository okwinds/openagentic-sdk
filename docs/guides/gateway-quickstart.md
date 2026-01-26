# OpenAgentic Gateway (Clawdbot-style) — Quickstart

This is an early, minimal “control plane” server living in `openagentic_gateway/`.

## Install

`pip install openagentic-sdk`

## Start (one command)

The Gateway has its own CLI entrypoint: `oag`.

Required env (same defaults as `oa` examples):

- `RIGHTCODE_API_KEY` (required)
- `RIGHTCODE_BASE_URL` (optional; default `https://www.right.codes/codex/v1`)
- `RIGHTCODE_MODEL` (optional; default `gpt-5.2`)

Run:

`oag --host 127.0.0.1 --port 18789`

State dir:

- Default: `~/.openagentic-sdk/gateway/`
  - sessions: `~/.openagentic-sdk/gateway/sessions/`
  - session map (sqlite): `~/.openagentic-sdk/gateway/session_map.sqlite3`
- Override: `oag --state-dir /path/to/dir`

## How it works (simple on purpose)

- **No extra queue/process by default**: the gateway runs `openagentic_sdk.run()` in-process.
- **Sessions**: gateway derives a deterministic `session_key` from `(agent_id, channel, account_id, peer_kind, peer_id)` and maps it to an SDK `session_id` via a local SQLite `SessionMap`.
- **Permissions**: uses `OA_PERMISSION_MODE` (default `default`), non-interactive. Safe tools are allowed; everything else is denied unless you later add an approval surface.

## Endpoints

- Health: `GET /health`
- Status (optionally protected): `GET /v1/gateway/status`
- Events (SSE): `GET /v1/events`
- Inbound chat (JSON): `POST /v1/chat/inbound`
- Telegram webhook (JSON): `POST /v1/webhooks/telegram/<account_id>`

## Auth (optional)

If `OA_GATEWAY_TOKEN` is set, all `/v1/*` endpoints require:

`Authorization: Bearer <OA_GATEWAY_TOKEN>`

`/health` stays public.

## Try it quickly

Telegram-style update (local test):

```bash
curl -sS -X POST "http://127.0.0.1:18789/v1/webhooks/telegram/default" \
  -H "Content-Type: application/json" \
  -d '{"update_id":1,"message":{"message_id":10,"chat":{"id":123,"type":"private"},"text":"hello"}}'
```
