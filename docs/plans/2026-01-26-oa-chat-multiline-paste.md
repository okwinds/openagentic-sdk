# Plan: `oa chat` Multi-line Paste as One Turn

Date: 2026-01-26

## Problem

`oa chat` currently reads input via `stdin.readline()` and immediately executes one agent turn per line.

This is a poor UX when the user pastes a multi-line prompt: the paste is consumed as multiple turns (one per line) and executed incrementally, which is almost never what the user intended.

Current code path:

- `openagentic_cli/repl.py` reads `line = stdin.readline()` and sends `prompt = line.rstrip("\n")` as the turn.

## Goal

When the user pastes multi-line content into `oa chat`, treat the entire paste as a *single* prompt/turn.

Secondary goal: provide a deterministic manual mode for multi-line input (works even when the terminal does not support paste detection).

## Non-goals

- We will not implement a full multi-line editor (textarea) in `oa chat` (no prompt_toolkit, no raw-mode line editing).
- We will not change tool execution semantics or session storage.

## How OpenCode Avoids the Problem (Comparison)

OpenCode's TUI uses a multi-line textarea input component and only submits on an explicit submit action, not on newline.

- `opencode/packages/opencode/src/cli/cmd/tui/component/prompt/index.tsx` uses a `textarea` and handles paste events without auto-submitting.

`oa chat` is intentionally simpler (line-based); we need an input-coalescing layer.

## Candidate Approaches

### A) Full multi-line editor / prompt_toolkit (Not chosen)

Pros:

- Best UX (real textarea, cursor movement, selection, history integration).

Cons:

- New dependency and large surface area.
- Harder to keep parity with current lightweight REPL.

### B) Bracketed paste mode (Chosen)

Modern terminals can wrap pasted content in special escape sequences when bracketed paste mode is enabled:

- Enable: `ESC[?2004h`
- Start of paste: `ESC[200~`
- End of paste: `ESC[201~`
- Disable: `ESC[?2004l`

References:

- iTerm2 "Paste Bracketing" wiki (control sequences): https://gitlab.com/gnachman/iterm2/-/wikis/Paste-Bracketing?version=html
- Conrad Irwin write-up (implementation checklist): https://cirw.in/blog/bracketed-paste

Plan:

- Enable bracketed paste mode while `oa chat` is running (TTY only).
- Change the input reader to detect `ESC[200~` and then read+accumulate lines until `ESC[201~` is seen.
- Strip the markers and submit the combined text as one turn.

This works without raw mode, because `stdin.readline()` will still surface the markers at the start/end of the pasted stream.

### C) Timing-based coalescing heuristic (Optional fallback; not default)

Read one line, then use `select`/`selectors` with a tiny idle window to absorb more lines if they are already buffered.

Pros:

- Works even when bracketed paste markers are absent.

Cons:

- Can merge fast manual input (false positives).
- Cross-platform complexity (Windows console).

We will avoid enabling this by default.

### D) Explicit `/paste` mode (Chosen as escape hatch)

User enters `/paste` in `oa chat`, then pastes/enters multiple lines, finishing with a sentinel line `/end`.

Pros:

- Deterministic and cross-platform.

Cons:

- Manual step.

## UX Rules

1) Default behavior stays the same for normal typing: one line == one turn.
2) If bracketed paste markers are observed, the pasted block is treated as one turn.
3) Pasted content is *not* interpreted as REPL commands even if it starts with `/exit` (it is treated as literal prompt text).
4) Manual multi-line input is available via `/paste` ... `/end`.

## Implementation Plan

1) Add a small input state machine in `openagentic_cli/repl.py`:

- Detect bracketed paste markers and coalesce multiple `readline()` results into one prompt.
- Strip `\x1b[200~` and `\x1b[201~` markers.
- Use `.rstrip("\r\n")` when converting the final combined buffer to prompt text.

2) Enable/disable bracketed paste mode for the duration of `run_chat()`:

- Only when both stdin and stdout are TTYs.
- Always disable in `finally`.

3) Add `/paste` REPL command:

- When invoked, read lines until a line that is exactly `/end`.
- Do not treat any content in paste mode as a REPL command.

## Test Plan (TDD)

Add unit tests that validate the input reader behavior without requiring a real TTY:

- Normal single-line input results in one prompt.
- Bracketed paste input with multiple lines results in one combined prompt.
- Bracketed paste containing `/exit` is not treated as a command.
- `/paste` mode reads until `/end` and submits combined prompt.

## Documentation

Update user docs to mention:

- Multi-line paste is coalesced into a single prompt when supported by the terminal.
- Manual mode: `/paste` to start, `/end` to finish.

---

## Results (DONE)

- Implementation: `openagentic_cli/repl.py`
- Tests: `tests/test_cli_repl_multiline_paste.py`
- Guide: `docs/guides/oa-chat-multiline-paste.md`
- Verification: `python -m unittest -q tests.test_cli_repl_multiline_paste`
