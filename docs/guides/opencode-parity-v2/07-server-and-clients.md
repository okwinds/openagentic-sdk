# v2-07 Server + Clients (Local HTTP API)

This repo includes a local HTTP server that provides an OpenCode-like API for sessions, streaming events, permissions/questions, sharing, and basic file/find operations.

## Start The Server

Run the server:

```
oa serve --host 127.0.0.1 --port 4096
```

Defaults:

- host: `127.0.0.1`
- port: `4096`

## Auth

The server can be protected by either Basic auth (OpenCode-style) or a Bearer token.

Basic auth:

```bash
export OPENCODE_SERVER_USERNAME=opencode
export OPENCODE_SERVER_PASSWORD=secret
```

Client header:

`Authorization: Basic <base64(username:password)>`

Bearer auth:

```bash
export OA_SERVER_TOKEN=secret
```

Client header:

`Authorization: Bearer secret`

If neither env var is set, the server allows requests (intended for local dev).

## Core Endpoints

Health:

- `GET /global/health`
- `GET /health` (legacy)

Event streaming (SSE):

- `GET /event`
  - emits `session.event` envelopes during prompt execution
- `GET /global/event`
  - emits `{ directory, payload }` wrappers (OpenCode style)

Sessions:

- `GET /session`
- `GET /session/status`
- `POST /session`
- `GET /session/:id`
- `PATCH /session/:id` (supports `title` and `time.archived`)
- `DELETE /session/:id`

Messages:

- `GET /session/:id/message` (OpenCode-like message view)
- `GET /session/:id/message/:messageID`
- `POST /session/:id/message` (runs prompt synchronously; returns latest assistant message)
- `POST /session/:id/prompt_async` (204; runs in background)
- `POST /session/:id/abort` (best-effort)

Revert / unrevert (timeline):

- `POST /session/:id/revert` with `{"messageID":"user_42"}` or `{"head_seq": 42}`
- `POST /session/:id/unrevert`

Sharing:

- `POST /session/:id/share`
- `DELETE /session/:id/share`
- `GET /share/:share_id`

Permissions / questions (server-mediated approvals):

- `GET /permission`
- `POST /permission/:id/reply` with `{"reply":"allow"}` or `{"reply":"deny"}`
- `GET /question`
- `POST /question/:id/reply` with `{"answers":["A"]}`
- `POST /question/:id/reject`

Find / file APIs (best-effort):

- `GET /find?pattern=...`
- `GET /find/file?query=...&limit=...`
- `GET /file?path=...` (directory listing)
- `GET /file/content?path=...` (file content, capped)
- `GET /file/status` (git porcelain)

Docs:

- `GET /doc` (minimal OpenAPI-like JSON)

## Notes For Clients/Automations

- Session IDs are validated strictly (32 hex chars). Path traversal is rejected.
- Request bodies are capped (2MB). Oversized payloads return 413.
- The message view is built from the append-only event log and filtered to the current head.
