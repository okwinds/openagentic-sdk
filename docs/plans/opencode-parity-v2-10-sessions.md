# OpenCode Parity v2 — Sessions (Status/Todo/Children/Fork/Transcript/Snapshot/Diff/Revert)

## Source of Truth (OpenCode)

- Session data model and message stream: `/mnt/e/development/opencode/packages/opencode/src/session/*`
- Todo storage: `/mnt/e/development/opencode/packages/opencode/src/session/todo.ts`
- Revert and cleanup semantics: `/mnt/e/development/opencode/packages/opencode/src/session/revert.ts`
- Snapshot subsystem (git-backed): `/mnt/e/development/opencode/packages/opencode/src/snapshot/index.ts`
- Server routes that expose sessions: `/mnt/e/development/opencode/packages/opencode/src/server/routes/session.ts`

## OpenCode Behavior (Detailed)

### 1) Todo

- Todo list is stored per session and updated by tool/UI.
- Storage is durable and an update emits an event.

OpenCode data shape:

```ts
// packages/opencode/src/session/todo.ts
type Todo = {
  content: string
  status: "pending" | "in_progress" | "completed" | "cancelled"
  priority: "low" | "medium" | "high"
  id: string
}
```

Reference: `/mnt/e/development/opencode/packages/opencode/src/session/todo.ts`

### 2) Snapshot tracking

- Uses an internal git directory under OpenCode data dir to track worktree snapshots.
- `Snapshot.track()` writes the current worktree to a git tree and returns hash.
- Supports `patch`, `diff`, `diffFull`, `restore` and `revert`.

Reference: `/mnt/e/development/opencode/packages/opencode/src/snapshot/index.ts`

### 3) Revert

- `SessionRevert.revert(sessionID, messageID, partID?)`:
  - asserts session not busy
  - finds revert boundary based on message/part
  - collects patches
  - ensures snapshot exists and reverts patches
  - computes diff metadata and stores it
  - updates session metadata with revert info
- `cleanup` removes messages/parts after revert point from storage.

Reference: `/mnt/e/development/opencode/packages/opencode/src/session/revert.ts`

### 4) Status and summary

- Session status is tracked (busy/idle) and exposed.
- Summary includes diff statistics.

References:

- `/mnt/e/development/opencode/packages/opencode/src/session/status.ts`
- `/mnt/e/development/opencode/packages/opencode/src/session/summary.ts`

## Current State (openagentic-sdk)

Status: PARTIAL

- Implemented:
  - Durable append-only events + rebuild.
  - Timeline head controls (checkpoint/set_head/undo/redo).
  - Fork from message with metadata.
  - Local share provider.
  - Todo persisted as `todos.json` under session dir when `TodoWrite` is invoked.
  - SSE event stream (`/event`, `/global/event`) for best-effort parity.

Key references:

- `openagentic_sdk/sessions/store.py`
- `openagentic_sdk/sessions/rebuild.py`
- `openagentic_sdk/sessions/diff.py`
- `openagentic_sdk/events.py`
- `openagentic_sdk/runtime.py` (`TodoWrite` persistence)

- Missing vs OpenCode:
  - Git-backed snapshot/revert system.
  - Revert cleanup semantics (delete messages/parts after revert boundary).
  - Session status tracking parity (busy/idle) and server exposure.
  - Session children listing endpoint.
  - Todo GET endpoint parity.
  - Fork endpoint parity.
  - Transcript capture/exposure.
  - Worktree diff computation parity (git-backed snapshot).

## Target Parity (Server Surface)

These are the minimum endpoints we implement for v2-10 parity in this repo:

- `GET /session/status` -> map of session id -> `{type: "idle" | "busy" | ...}`
- `GET /session/{id}/children` -> list of child sessions
- `GET /session/{id}/todo` -> list of todos (OpenCode `Todo.Info[]` shape)
- `POST /session/{id}/fork` -> new session info
- `GET /session/{id}/diff?messageID=...` -> worktree diff list for the snapshot at that boundary

Notes:

- We already expose `POST /session/{id}/revert` + `POST /session/{id}/unrevert`, but these are timeline-head only.
  For parity, `/revert` must additionally support reverting the worktree via snapshots + cleanup semantics.

## Data Model (This Repo)

We keep the existing on-disk layout under `FileSessionStore.root_dir`.

Session directory:

```
<root>/sessions/<session_id>/
  meta.json
  events.jsonl
  todos.json          # written by TodoWrite
  transcript.jsonl    # NEW: minimal, stable transcript/event log for UI
```

Key metadata fields (stored under `meta.json:metadata`):

- `title` (string)
- `time.archived` (float seconds since epoch)
- `parent_session_id` (string) for fork/task sessions
- `parent_head_seq` (int) for forks
- `parent_tool_use_id` (string) for `Task`-spawned child sessions

Todo storage:

- We will accept both the existing `TodoWrite` shape (with `activeForm`) and the OpenCode todo shape.
- We will persist a canonical todo list and serve OpenCode-like `Todo.Info[]` from `GET /session/{id}/todo`.

Transcript storage:

- A line-oriented JSONL file that contains user/assistant text in a stable format.
- This is independent from `events.jsonl` (events are for audit; transcript is for UI diffs + share rendering).

## Plan (No-Compromise Implementation)

1) Implement Snapshot subsystem parity (git-backed) with a configurable storage root.
2) Implement SessionRevert parity:
   - snapshot capture per message/part
   - revert to message/part
   - cleanup of timeline data beyond revert point
   - diff metadata
3) Expose todo/status/children/revert/diff/share via HTTP server parity endpoints.

## Security Model

- Snapshot/revert executes git commands:
  - must be permission-gated
  - must be constrained to the project worktree root
- Must not delete or overwrite files outside the intended project root.

## TDD

- Integration tests using temp git repo:
  - track snapshot
  - modify files
  - diff
  - revert
- Tests for revert cleanup removing later session events.

## Acceptance Checklist

- `GET /session/{id}/children` returns all sessions whose `meta.json:metadata.parent_session_id == id`.
- `POST /session/{id}/fork` creates a new session with `parent_session_id` and `parent_head_seq`.
- `GET /session/{id}/todo` returns a JSON array of todos in OpenCode shape (even if written in legacy shape).
- `/session/status` returns `busy` while a prompt is running and returns `idle` when complete.
- Transcript file is written and does not leak tool inputs/outputs by default.
- All new functionality constrained to the project root and does not allow path traversal.
