# `oa chat`: Multi-line Paste (Single Turn)

`oa chat` is line-based by design, but multi-line pastes are treated as a *single* prompt/turn to avoid accidental “one turn per line” execution.

## Bracketed paste (automatic)

When both stdin and stdout are TTYs, `oa chat` enables bracketed paste mode and coalesces pasted content wrapped by:

- start: `ESC[200~`
- end: `ESC[201~`

Everything between the markers (including internal newlines) becomes one prompt.

Important: pasted content is treated as literal prompt text, not as a REPL command (so pasting `/exit` won’t exit).

### Windows / PowerShell note

On Windows consoles, receiving bracketed paste markers requires enabling “virtual terminal input” mode on stdin. `oa chat` enables this automatically while it runs.

## Manual paste mode (fallback)

Use this when the terminal doesn’t support bracketed paste markers:

- Enter `/paste`
- Paste/type multiple lines
- Finish with a line that is exactly `/end` (trailing whitespace allowed)

The collected block is submitted as one prompt.

If bracketed paste mode is enabled, the `ESC[200~` / `ESC[201~` markers are stripped in this mode as well (so they never appear in the prompt text).

## Fallback for terminals without markers

If no bracketed paste markers are observed, `oa chat` still tries to detect multi-line pastes by coalescing any already-buffered extra lines on TTY stdin into the same turn.

## Implementation

- Reader: `openagentic_cli/repl.py` (`read_repl_turn`)
- REPL command: `/paste` … `/end`
