# Parity 08: Compaction (Overflow + Summary Pivot + Tool Output Pruning)

Status: implemented (initial slice) in this repo:

- Overflow detection (usage-based) + auto-compaction when configured
- Hard compaction summary pivot stored as `assistant.message` with `is_summary=true`
- Soft compaction tool-output pruning via append-only `tool.output_compacted` markers
- Rebuild filtering to the latest summary pivot for future model inputs
- Runtime integration + tests

Key files:

- `openagentic_sdk/compaction.py`
- `openagentic_sdk/runtime.py`
- `openagentic_sdk/sessions/rebuild.py`
- `openagentic_sdk/events.py`
- `tests/test_compaction_auto_and_prune.py`

## Analysis

OpenCode implements:

- Overflow detection against model context budget.
- Hard compaction (summary pivot) with a dedicated compaction prompt/agent.
- Soft compaction (tool output pruning) by marking outputs as compacted.

References:

- Implementation: `opencode/packages/opencode/src/session/compaction.ts`
- Design: `opencode/COMPACTION.md`

Current repo: design doc exists (`COMPACTION.md`) but runtime implementation is missing.

## Plan

- Add compaction state machine to Python runtime:
  - detect overflow using provider usage metadata
  - schedule compaction marker
  - run tool-less compaction pass
  - filter message history to post-pivot window
  - prune old tool outputs in serialization layer
- Provide config toggles: `compaction.auto`, `compaction.prune`.

## TDD

- Tests that:
  - simulate overflow and assert compaction marker + summary message appear
  - assert pruned tool outputs serialize with placeholders
