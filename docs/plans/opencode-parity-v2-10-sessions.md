# OpenCode Parity v2 — Sessions (Status/Todo/Fork/Revert/Snapshot/Diff)

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

Key references:

- `openagentic_sdk/sessions/store.py`
- `openagentic_sdk/sessions/rebuild.py`
- `openagentic_sdk/sessions/diff.py`
- `openagentic_sdk/events.py`
- `openagentic_sdk/runtime.py` (`TodoWrite` persistence)

- Missing vs OpenCode:
  - Git-backed snapshot/revert system.
  - Revert cleanup semantics (delete messages/parts after revert boundary).
  - Session status tracking and server exposure.
  - Diff computation parity for worktree changes.

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
