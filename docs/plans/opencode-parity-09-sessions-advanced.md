# Parity 09: Sessions Advanced (Diff/Revert/Fork/Share/Timeline)

## Analysis

OpenCode supports:

- Revert/undo via snapshots.
- Diff per message.
- Fork session from message.
- Share/unshare sessions.

References:

- `opencode/packages/opencode/src/session/revert.ts`
- `opencode/packages/opencode/src/session/summary.ts`
- `opencode/packages/opencode/src/share/share-next.ts`
- `opencode/packages/opencode/src/server/routes/session.ts`

Current repo: durable event log + resume only.

## Plan

- Add an optional worktree snapshot/diff subsystem:
  - capture file checkpoints per message
  - compute diffs
  - revert to a checkpoint
- Extend session metadata model to include parent/child and fork points.
- Add share subsystem as optional module.

## TDD

- Tests that create temp worktrees, apply edits, compute diffs, revert.
