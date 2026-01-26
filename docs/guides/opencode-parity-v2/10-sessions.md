# OpenCode Parity v2-10: Sessions

This repo uses an append-only event log for sessions (`events.jsonl`) and builds an OpenCode-like message view on top.
v2-10 fills in several missing session APIs and on-disk artifacts so the local server behaves closer to OpenCode.

## On-disk layout

Under your `OPENAGENTIC_SDK_HOME` (or the configured session root), each session lives at:

`sessions/<session_id>/`

Files:

- `meta.json`: session metadata (title, archive time, parent links, share id)
- `events.jsonl`: append-only audit log (includes tool calls/results)
- `todos.json`: persisted todo list when `TodoWrite` runs
- `transcript.jsonl`: minimal conversation transcript (user/assistant text only)

Notes:

- `transcript.jsonl` intentionally excludes tool inputs/outputs.
- Older sessions may not have `todos.json` or `transcript.jsonl` until they are written.

## Local server endpoints

These endpoints are served by `openagentic_sdk/server/http_server.py`.

- `GET /session/status`
  - Returns a map of session id -> status.
  - Status is `busy` while a prompt is running, otherwise `idle`.

- `GET /session/{id}/children`
  - Returns child sessions where `meta.json:metadata.parent_session_id == {id}`.
  - Includes forks and tool-spawned child sessions.

- `POST /session/{id}/fork`
  - Forks a session at a message boundary.
  - Accepts `{ "messageID": "user_<n>" }` (OpenCode-like message id in this repo).
  - The fork excludes the message at `messageID` and beyond.

- `GET /session/{id}/todo`
  - Returns a list of todos in an OpenCode-like shape:
    `{content, status, priority, id}`.
  - Back-compat: legacy `TodoWrite` items with `activeForm` are normalized.

- `GET /session/{id}/transcript`
  - Returns `{ "session_id": "...", "entries": [...] }`.
  - Entries are derived from `transcript.jsonl`.

## TodoWrite shape

`TodoWrite` accepts both:

- OpenCode-like todos: `{content, status, priority, id}`
- Legacy todos: `{content, activeForm, status}`

Todos are persisted in a canonical OpenCode-like form in `todos.json`.

## Share safety

Sharing a session stores a payload that includes:

- `events`: tool inputs/outputs are redacted (inputs become `{}`, outputs become `null`)
- `transcript`: transcript entries (user/assistant text)

This is best-effort and does not attempt to redact secrets inside user/assistant text.
