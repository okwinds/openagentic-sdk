# OpenCode Parity v2 — Compaction (Overflow + Prune + Summary Pivot)

## Source of Truth (OpenCode)

- Compaction logic: `/mnt/e/development/opencode/packages/opencode/src/session/compaction.ts`
- Prompt loop integration: `/mnt/e/development/opencode/packages/opencode/src/session/prompt.ts`
- Design doc: `/mnt/e/development/opencode/COMPACTION.md`

## OpenCode Behavior (Detailed)

### Overflow detection

- Uses model token limits:
  - `context = model.limit.context`
  - `count = input + cache.read + output`
  - output reserve = `min(model.limit.output, SessionPrompt.OUTPUT_TOKEN_MAX)`
  - usable = `model.limit.input || (context - outputReserve)`
  - overflow if `count > usable`
- Disabled if `config.compaction.auto === false` or model context is 0.

Reference: `SessionCompaction.isOverflow()`.

Also note:

- `SessionPrompt.OUTPUT_TOKEN_MAX` defaults to 32_000 (env configurable). It caps the output reserve used in overflow math.
- Overflow uses `input + cache.read + output` (does not include reasoning or cache.write).

### Pruning tool outputs

- Defaults:
  - `PRUNE_MINIMUM = 20_000`
  - `PRUNE_PROTECT = 40_000`
  - protected tools include `skill`
- Walks backwards through message parts and counts estimated tool-output tokens.
- Skips pruning until at least 2 user turns are present.
- Stops when:
  - encountering a summary message
  - encountering already-compacted tool outputs
- Only applies pruning if `prunedTokens > PRUNE_MINIMUM`.

Reference: `SessionCompaction.prune()`.

Pruning representation in model input:

- Pruning does not delete stored outputs. It marks tool parts as compacted.
- When building model messages, compacted tool outputs are replaced with the exact placeholder: `[Old tool result content cleared]` and attachments are removed.

Reference: `/mnt/e/development/opencode/packages/opencode/src/session/message-v2.ts` (`toModelMessages`).

### Summary pivot

- Creates a dedicated assistant summary message (mode/agent "compaction", `summary: true`).
- Allows plugins to inject context or replace the compaction prompt:
  - hook: `experimental.session.compacting`
- If compaction was auto-triggered and the result is continue, it inserts a synthetic "Continue" user message.

Reference: `SessionCompaction.process()`.

Hard-compaction pivot behavior (history windowing):

- Model inputs after a successful compaction are filtered to the latest compaction pivot.
- The pivot is considered "completed" only if the assistant summary message has `summary: true` and `finish` set.
- The filter keeps messages from the corresponding compaction-marker user message forward.

Reference: `/mnt/e/development/opencode/packages/opencode/src/session/message-v2.ts` (`filterCompacted`).

Compaction marker question:

- A user message containing a compaction part is rendered to the model as the user text: `What did we do so far?`.

Reference: `/mnt/e/development/opencode/packages/opencode/src/session/message-v2.ts`.

## Current State (openagentic-sdk)

- Implemented (partial) in `openagentic_sdk/compaction.py` and `openagentic_sdk/runtime.py`.
- Differences:
  - thresholds/protected tools differ
  - no "2 turns" guard
  - no plugin hook for compaction context/prompt
  - compaction is not modeled as an agent with per-agent config
  - no synthetic continue message

Status update (this repo):

- Prune traversal now matches OpenCode semantics:
  - requires >= 2 user turns
  - stops at summary pivot
  - stops at already-compacted tool output (idempotence boundary)
  - protects tool name `Skill`
  - applies only if prunedTokens > min_prune_tokens (default 20_000)
- Compaction marker is rendered to the model exactly as: `What did we do so far?`.
- Plugin hook parity added:
  - `HookEngine.session_compacting` allows plugins to inject compaction context/prompt.
  - Runtime uses it before running the compaction model call.

Additional parity gaps (must fix):

- Tool-output pruning should:
  - skip pruning until at least 2 user turns exist
  - stop at summary pivot
  - stop at the first already-compacted tool output (idempotence boundary)
  - protect tool type `skill`
  - only apply if prunedTokens > 20_000

- Compaction execution should be a distinct agent-mode with tools denied (defense in depth).

## Plan (No-Compromise Implementation)

- Align overflow math to OpenCode model limits rather than heuristics.
- Model compaction as a first-class agent (configurable model/provider).
- Harden compaction prompt:
  - add explicit instruction to omit secrets and avoid reproducing credentials
  - ensure plugin-provided prompt/context is treated as untrusted

## Security / Privacy Notes

- The summary pivot is a high-salience message; ensure we do not accidentally preserve secrets (consider redaction policies or "do not include secrets" instructions in the compaction agent prompt).
- Pruning is not deletion; be explicit in docs/UX.
- Plugin hook `experimental.session.compacting` can inject prompt/context; treat as untrusted extension code.

## TDD

- Overflow tests with fake model limits and token counters.
- Prune traversal tests:
  - summary boundary
  - 2-turn guard
  - protected tools
  - min-prune threshold
- Compaction process tests:
  - plugin-injected prompt
  - auto continue message insertion
