# OpenCode Parity v2 — Server + Clients (CLI/TUI)

## Source of Truth (OpenCode)

- Session routes: `/mnt/e/development/opencode/packages/opencode/src/server/routes/session.ts`
- Server: `/mnt/e/development/opencode/packages/opencode/src/server/*`
- TUI: `/mnt/e/development/opencode/packages/opencode/src/cli/cmd/tui/*`

Additional route groups:

- `/mnt/e/development/opencode/packages/opencode/src/server/server.ts` (root app + `/event` SSE + misc endpoints)
- `/mnt/e/development/opencode/packages/opencode/src/server/routes/global.ts`
- `/mnt/e/development/opencode/packages/opencode/src/server/routes/permission.ts`
- `/mnt/e/development/opencode/packages/opencode/src/server/routes/question.ts`
- `/mnt/e/development/opencode/packages/opencode/src/server/routes/pty.ts`
- `/mnt/e/development/opencode/packages/opencode/src/server/routes/mcp.ts`
- `/mnt/e/development/opencode/packages/opencode/src/server/routes/provider.ts`
- `/mnt/e/development/opencode/packages/opencode/src/server/routes/config.ts`
- `/mnt/e/development/opencode/packages/opencode/src/server/routes/project.ts`
- `/mnt/e/development/opencode/packages/opencode/src/server/routes/file.ts`
- `/mnt/e/development/opencode/packages/opencode/src/server/routes/experimental.ts`
- `/mnt/e/development/opencode/packages/opencode/src/server/routes/tui.ts`

## OpenCode Server Surface (Partial Inventory)

OpenCode exposes (high-level):

- `GET /session` list sessions (filters: directory, roots, start, search, limit)
- `GET /session/status` session status map
- `GET /session/:sessionID` get session
- `GET /session/:sessionID/children` fork children
- `GET /session/:sessionID/todo` todo list
- `POST /session` create
- `DELETE /session/:sessionID` delete
- `PATCH /session/:sessionID` update

Plus (not exhaustive):

- `GET /event` (SSE bus)
- `GET /global/health`, `GET /global/event` (SSE)
- `POST /session/:id/message` (prompt), `POST /session/:id/prompt_async`
- `POST /session/:id/abort`, `POST /session/:id/summarize` (compaction)
- `POST /session/:id/revert`, `POST /session/:id/unrevert`
- `POST /session/:id/share`, `DELETE /session/:id/share`
- `GET /permission` + reply, `GET /question` + reply/reject
- `/pty/*` + websocket
- `/provider/*`, `/config/*`, `/project/*`, `/mcp/*`
- `/find`, `/file/*`
- `/tui/*` control queue

And many more under `session.ts` (messages, streaming, prompt loop, snapshots, revert, share, etc).

## Current State (openagentic-sdk)

- Minimal local HTTP server/client exists:
  - `openagentic_sdk/server/http_server.py`
  - `openagentic_sdk/server/http_client.py`
- Contract tests exist:
  - `tests/test_http_server_surface.py`
  - `tests/test_http_client_smoke.py`

What it currently supports (non-parity):

- `GET /health`

Status update (this repo):

- Server now includes a first batch of OpenCode-like endpoints:
  - `GET /global/health`
  - `GET /event` (SSE bus; publishes `session.event` envelopes)
  - `GET /session` returns an array of session infos
  - `GET /session/status` returns `{ sessionID: {type:"idle"} }`
  - `PATCH /session/:id` updates `title` and `time.archived`
  - `DELETE /session/:id`
  - `GET /session/:id/message` returns an OpenCode-like message list (best-effort from events)
  - `POST /session/:id/message` returns the latest assistant message in that view
  - `POST /session/:id/prompt_async` (204) runs in background
  - `POST /session/:id/abort` sets a per-session abort flag (best-effort)

- Debug endpoints retained:
  - `GET /session/:id/events` (raw event log)
  - `GET /session/:id/model_messages` (provider-history rebuild)

## Parity Target

- Implement a parity-grade server API compatible with OpenCode semantics:
  - sessions CRUD
  - message submission + streaming
  - status/timeline/todo/share
  - fork/children
  - revert/diff endpoints if OpenCode exposes them

Important: OpenCode uses SSE (`/event`, `/global/event`) as the primary mechanism for live UI updates.
For parity, our server must expose an SSE bus and publish session events during prompt execution.

## Security Model

- Bind to loopback by default.
- Support OpenCode-style Basic auth gate when configured:
  - env `OPENCODE_SERVER_PASSWORD` => `Authorization: Basic ...`
- Support an OpenAgentic bearer token gate:
  - env `OA_SERVER_TOKEN` => `Authorization: Bearer ...`
- Enforce request size limits.
- Validate and sanitize session IDs and file paths.

Do not expose dangerous operations without strong gating:

- Any endpoint that triggers tool execution MUST be protected by auth and (ideally) loopback-only.
- If we later add `/session/:id/shell` or `/pty/*`, implement explicit allowlists and audit logs.

## TUI Parity (Python)

Parity target for TUI:

- Session list + switch
- Live streaming of assistant output
- Tool call visibility + approvals UI
- Todo view/edit
- Command palette (slash commands)

Implementation approach:

- Use an optional dependency (e.g. `textual`) behind extras, to keep core SDK lean.
- Provide a non-interactive fallback (current `oa chat`) for environments without TTY.

## TDD

- Contract tests for all server endpoints (status codes, schemas, streaming behavior).
- Security tests:
  - rejects oversized payloads
  - rejects missing/invalid auth token
  - rejects path traversal attempts

## Work Plan (Waterfall per Feature)

1) Analysis: route-by-route mapping OpenCode => openagentic-sdk primitives.
2) Plan/spec: document exact request/response shapes and streaming semantics.
3) TDD: contract tests for each route.
4) Implement: server + client + CLI wiring.
5) Review: security + edge cases.
