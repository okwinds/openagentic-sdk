# Context Compaction: Auto-Trigger, Summarize, Prune (Portable Design)

This document describes the *design and lifecycle* of OpenCode-style “compaction”: how it detects context overflow, when it auto-triggers, how it compresses conversational state, and what prompts it uses. It is written to be *portable* so another SDK can reproduce the same behavior without copying code structure.

---

## 1) What “Compaction” Solves

Long-running agent sessions eventually hit a model’s context window. Compaction is a **two-layer strategy**:

1. **Hard compaction (summary pivot):** Replace old conversation turns with a single assistant “summary” message that carries forward the important state.
2. **Soft compaction (tool-output pruning):** Keep the conversation turns, but hide old tool outputs from the model input while still retaining them in storage/UI.

The system uses hard compaction when the model’s context is full; it uses pruning as ongoing maintenance to reduce token pressure from long tool outputs.

---

## 2) Data Model (Minimal Requirements)

To reproduce this behavior, your SDK needs these concepts:

- **Session**: an ordered stream of messages.
- **Message**: has `role` = user/assistant plus metadata.
- **Message Parts**: each message can contain multiple typed parts (text, file, tool-call, etc.).
- **Tool Part** (assistant-side): stores a tool name + input + output and timestamps.
- **Compaction Marker Part** (user-side): a special part that *queues a compaction job*; includes `auto: boolean`.
- **Summary Assistant Message Flag**: a boolean marker on an assistant message indicating “this message is the compaction summary”.
- **Tool Output Compacted Flag**: a timestamp or boolean on a tool part meaning “do not send its output content to the model”.

---

## 3) When Auto-Compaction Triggers

Auto-compaction triggers when a completed model step would overflow the usable input budget.

### 3.1 Overflow Check (Token Budget)

Definitions:

- `contextLimit`: model context window size (tokens). If `contextLimit == 0`, treat as “unlimited” and never auto-compact.
- `outputLimit`: model max output tokens.
- `globalOutputCap`: a product-level cap on output tokens (prevents extreme outputs from consuming the whole context).
- `outputReserve = min(outputLimit, globalOutputCap)` (fallback to `globalOutputCap` if `outputLimit` is not set).
- `inputLimit`: some models expose a dedicated max-input limit; if present, prefer it.

On each completed step, compute:

```
total = inputTokens + cacheReadTokens + outputTokens
usable = inputLimit ?? (contextLimit - outputReserve)
overflow = (total > usable)
```

Auto-compaction is enabled by default, but can be disabled via configuration (e.g., `compaction.auto=false`).

### 3.2 Trigger Timing

The check happens **after** a model step finishes (when token usage is known). If overflow is detected:

- Stop further generation for this loop iteration.
- Schedule a compaction job by enqueuing a compaction marker (see §4).

---

## 4) Hard Compaction (Summary Pivot) Lifecycle

Hard compaction is implemented as a **two-phase state machine**: *schedule → execute → resume*.

### 4.1 Schedule: enqueue a compaction marker

When overflow is detected, the runtime appends a new *user message* containing a **compaction marker part**:

- `auto: true` if triggered automatically
- (manual entrypoints may set `auto: false`)

This design is important: it makes compaction a first-class queued task in the same message stream, so the normal session loop can pick it up deterministically.

### 4.2 Execute: run a dedicated “compaction agent”

On the next loop iteration, the runtime prioritizes pending compaction markers and runs a compaction pass:

- Use a **dedicated compaction agent** that is:
  - **Hidden/internal**
  - **Tool-less / no side effects** (all tools denied)
  - Tuned for summarization
- Model selection:
  - Prefer a compaction-specific model if configured.
  - Otherwise reuse the current session’s model (so compaction works everywhere).

Inputs to the compaction call:

- **Message history**: the current session message stream (typically already filtered to the “post-last-compaction window”; see §4.4).
- **A compaction “question”** injected into the user side of the conversation (see prompts in §6).
- **A final explicit instruction** asking the model to produce a continuation-ready summary/prompt (see §6.2).
- **No tools** provided (tools map is empty).

Output:

- Store the result as a new **assistant message flagged as `summary=true`**.
- Emit a “compacted” event (optional; useful for UI updates).

### 4.3 Resume: optionally auto-continue

If compaction was auto-triggered (`auto=true`) and the compaction pass succeeded, the runtime can append a **synthetic user message** like:

> “Continue if you have next steps”

This keeps the agent loop moving without waiting for a human message, and avoids “stalling right after compaction”.

### 4.4 Future Context: filter history to the latest summary pivot

After a compaction summary exists, the runtime should stop sending the full pre-compaction history to the model. Instead:

- Walk backward from the newest message.
- Stop once you reach the **compaction marker** that has a corresponding **completed summary assistant message**.
- Keep only messages from that point forward (including the summary message).

Effectively, the compaction summary becomes the *single source of truth* for everything before the pivot.

This filtering is critical; without it, you would still exceed the context window even after producing a summary.

---

## 5) Soft Compaction (Tool-Output Pruning)

Tool outputs can be huge (logs, diffs, generated files). Even with hard compaction, the “recent window” can bloat due to tool output parts.

Pruning is a background cleanup pass that **does not delete data**, but prevents old tool outputs from being included in the model input.

### 5.1 Pruning Strategy

Scan backwards over messages (usually *since the latest summary pivot*) and consider only:

- Completed tool parts
- Excluding protected tool types (example: keep `skill` outputs because they act like authoritative instructions)

Heuristics:

- Keep the most recent ~1–2 user turns unpruned (avoid erasing the short-term working set).
- Stop scanning once you hit:
  - The latest summary pivot message, or
  - A tool part already marked as compacted (idempotence boundary)

Token accounting:

- Estimate tool output token cost using a lightweight heuristic (e.g., `tokens ≈ chars/4`).

Thresholds (example values used in practice):

- `PROTECT = 40_000` tokens of most-recent tool output content to keep.
- `MIN_PRUNE = 20_000` tokens minimum before applying pruning (avoid churn for small gains).

Algorithm sketch:

1) Accumulate `totalToolOutputTokens` while walking backwards through tool outputs.  
2) Once `totalToolOutputTokens > PROTECT`, start adding older tool parts to a `toPrune` list.  
3) If the estimated pruned tokens exceeds `MIN_PRUNE`, mark each selected tool part with `time.compacted = now()`.

### 5.2 How Pruned Tool Parts Serialize to the Model

When converting stored messages to model input:

- If a tool part is marked compacted:
  - Replace its output text with a small placeholder, e.g.:
    - `[Old tool result content cleared]`
  - Drop binary/media attachments for that tool output
- Otherwise include full output as usual

Important: the real tool output remains in storage/UI; pruning affects *only what is fed back into the model*.

---

## 6) Prompts Used by Compaction

Compaction quality is very sensitive to prompting. The design uses **two layers**: a system prompt for the compaction agent + a user instruction appended at runtime.

### 6.1 Compaction Agent System Prompt (Template)

Use a stable, tool-less summarizer system prompt. The following template mirrors the behavior:

```
You are a helpful AI assistant tasked with summarizing conversations.

When asked to summarize, provide a detailed but concise summary of the conversation.
Focus on information that would be helpful for continuing the conversation, including:
- What was done
- What is currently being worked on
- Which files are being modified
- What needs to be done next
- Key user requests, constraints, or preferences that should persist
- Important technical decisions and why they were made

Your summary should be comprehensive enough to provide context but concise enough to be quickly understood.
```

### 6.2 Runtime Compaction Instruction (Default User Prompt)

Append a final user message that explicitly requests a continuation-ready result:

```
Provide a detailed prompt for continuing our conversation above. Focus on information that would be helpful for continuing the conversation, including what we did, what we're doing, which files we're working on, and what we're going to do next considering new session will not have access to our conversation.
```

Optionally prepend/append extra context lines from plugins/extensions (e.g., “current branch”, “current goals”, “known constraints”).

### 6.3 Marker-to-Text Injection (“What did we do so far?”)

When the user message contains a compaction marker part, inject a simple textual question into the user content stream:

```
What did we do so far?
```

This helps steer the model toward summarization even before it reads the longer instruction in §6.2.

---

## 7) Configuration Surface (Portable)

Expose at least:

- `compaction.auto` (default: true): enable/disable auto-compaction on overflow
- `compaction.prune` (default: true): enable/disable tool-output pruning

Optional:

- Override model/provider for compaction runs
- Adjustable thresholds (`PROTECT`, `MIN_PRUNE`)
- Pluggable token estimator

---

## 8) Migration Checklist (Other SDK)

- Represent compaction as an explicit queued task (marker part) rather than an implicit side effect.
- Use a dedicated tool-less summarizer agent (or enforce “no tools” at call-time).
- Implement post-step overflow detection based on actual usage tokens + a clear budget formula.
- After compaction completes, filter future history to the post-pivot window (or you will still overflow).
- Prune tool outputs by *marking* parts and changing serialization, not deleting stored content.
- Protect high-value tool outputs (e.g., skills/instructions) from pruning.

