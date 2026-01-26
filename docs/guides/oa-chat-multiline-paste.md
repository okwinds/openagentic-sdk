# `oa chat`: Multi-line Paste (Single Turn)

`oa chat` is line-based by design, but multi-line pastes are treated as a *single* prompt/turn to avoid accidental “one turn per line” execution.

## Bracketed paste (automatic)

When both stdin and stdout are TTYs, `oa chat` enables bracketed paste mode and coalesces pasted content wrapped by:

- start: `ESC[200~`
- end: `ESC[201~`

Everything between the markers (including internal newlines) becomes one prompt.

Important: pasted content is treated as literal prompt text, not as a REPL command (so pasting `/exit` won’t exit).

## Manual paste mode (fallback)

Use this when the terminal doesn’t support bracketed paste markers:

- Enter `/paste`
- Paste/type multiple lines
- Finish with a line that is exactly `/end` (trailing whitespace allowed)

The collected block is submitted as one prompt.

## Implementation

- Reader: `openagentic_cli/repl.py` (`read_repl_turn`)
- REPL command: `/paste` … `/end`

