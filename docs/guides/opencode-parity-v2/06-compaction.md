# v2-06 Compaction (Overflow + Prune + Summary Pivot)

This guide explains how session compaction works and how to tune it.

## What Compaction Does

Compaction is a safety mechanism to keep long sessions usable:

- If the model context would overflow, the runtime can insert a summary pivot.
- It can also prune old tool outputs (without deleting them from disk).

There are two distinct behaviors:

1) Summary pivot: create a dedicated assistant summary message.
2) Tool-output pruning: replace older tool outputs in the next model input with:
   - `[Old tool result content cleared]`

## The Compaction Marker

When compaction runs, the model sees a user message equivalent to:

```
What did we do so far?
```

This is intentional: it anchors the summarization to "session so far".

## Pruning Semantics (OpenCode Parity)

Pruning is conservative and rule-based:

- It will not prune until there are at least 2 user turns.
- It stops scanning older history when it reaches a summary pivot.
- It stops scanning older history when it hits an already-compacted tool output (idempotence boundary).
- It never prunes `Skill` tool outputs.
- It only applies pruning if prunedTokens is greater than `min_prune_tokens` (default 20_000).

Pruning does not delete stored events. It only changes what future model inputs include.

## Configuring Compaction

In `opencode.json`:

```json
{
  "compaction": {
    "auto": true,
    "prune": true,
    "context_limit": 9000
  }
}
```

Notes:

- `auto`: enable/disable auto compaction
- `prune`: enable/disable tool-output pruning
- `context_limit`: the threshold used by the runtime for overflow behavior in the CLI

## Plugin Hook: `session_compacting`

Plugins can influence the compaction prompt/context.

Hook point:

- `HookEngine.session_compacting`

The plugin can return an override object:

- `context`: list of extra context strings appended to the compaction prompt
- `prompt`: a full replacement prompt string

If the hook blocks, compaction is skipped.

## Security Notes

- Summaries are high-salience messages; do not include secrets.
- Plugins can inject compaction prompt/context; treat plugin code as untrusted.
