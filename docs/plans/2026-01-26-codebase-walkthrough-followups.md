# Codebase Walkthrough Follow-ups (TDD)

Date: 2026-01-26

**Goal:** Continue the repo-wide code review and fix the next highest-impact issues with TDD + per-fix docs, then write results back into this plan.

**Scope constraints (local sandbox):** This environment cannot create sockets (`socket.socket()` raises `PermissionError`). All new tests in this plan must avoid binding/listening sockets and should rely on unit-level seams/mocks.

---

## Task 1: Finish `oa chat` multi-line paste support (CLI REPL)

**Problem:** `oa chat` previously consumed pasted multi-line prompts as multiple turns. A bracketed-paste coalescer + `/paste`…`/end` fallback was started, but the implementation needs cleanup (import ordering / line endings) and documentation.

**Files:**
- Modify: `openagentic_cli/repl.py`
- Modify: `tests/test_cli_repl_multiline_paste.py`
- Create doc: `docs/guides/oa-chat-multiline-paste.md`
- Update: `docs/plans/2026-01-26-oa-chat-multiline-paste.md` (add DONE results)

**TDD (unit tests, no TTY required):**
- `test_read_turn_single_line`
- `test_read_turn_bracketed_paste_multiple_lines`
- `test_read_turn_bracketed_paste_same_line`
- `test_read_turn_manual_paste_mode_until_end`

**Implementation notes:**
- Keep imports at the top of the file; ensure LF line endings.
- In `run_chat()`, enable bracketed paste mode only when stdin/stdout are TTY; always disable in `finally`.
- Never treat pasted content as a REPL command (even if it starts with `/exit`).

---

## Task 2: MCP OAuth callback server `_pending` thread safety

**Problem:** `OAuthCallbackServer._pending` is accessed from both the HTTP handler thread and the asyncio event loop without synchronization; this can race and corrupt state or crash in rare cases.

**Files:**
- Modify: `openagentic_sdk/mcp/oauth_callback.py`
- Create: `tests/test_mcp_oauth_callback_pending_thread_safety.py`
- Create doc: `docs/guides/mcp-oauth-callback-thread-safety.md`

**TDD:**
- Add a deterministic unit test that replaces `_pending` with a guard mapping asserting all access happens while holding a lock.
- Ensure both handler-path resolution and `close()` clearing/failing of pending futures are lock-protected.

**Implementation notes:**
- Add a `threading.Lock` field (e.g., `_pending_lock`) and guard all `_pending` operations.
- Factor the callback parsing/resolution into a helper method so it is testable without binding sockets.

---

## Task 3: HTTP server permission/question queue thread safety

**Problem:** In `OpenAgenticHttpServer`, `pending_permissions` / `pending_questions` (and their answer queues) are shared across threads without a lock. `/permission` and `/question` list operations can race with background prompt execution, risking `RuntimeError` and inconsistent state.

**Files:**
- Modify: `openagentic_sdk/server/http_server.py`
- Create: `tests/test_http_server_prompt_queue_thread_safety.py`
- Create doc: `docs/guides/http-server-prompt-queue-thread-safety.md`

**TDD:**
- Introduce a small helper object wrapping the dicts and a lock.
- Test deterministically by swapping in guard dicts that assert the lock is held during all mutations and reads.

**Implementation notes:**
- Keep the change minimal: a helper class with `add/remove/list` methods used by both the request handler and the internal permission gate callbacks.

---

## Results (DONE)

- **Task 1: `oa chat` multi-line paste**
  - Code: `openagentic_cli/repl.py`
  - Tests: `tests/test_cli_repl_multiline_paste.py`
  - Doc: `docs/guides/oa-chat-multiline-paste.md`
  - Notes: bracketed paste is coalesced into one prompt; `/paste`…`/end` provides a deterministic fallback; pasted content is not treated as a REPL command.

- **Task 2: MCP OAuth callback pending thread safety**
  - Code: `openagentic_sdk/mcp/oauth_callback.py` (`_pending_lock`, `_handle_callback_path`)
  - Tests: `tests/test_mcp_oauth_callback_pending_thread_safety.py`
  - Doc: `docs/guides/mcp-oauth-callback-thread-safety.md`

- **Task 3: HTTP server prompt queue thread safety**
  - Code: `openagentic_sdk/server/http_server.py` (`_PromptQueues`)
  - Tests: `tests/test_http_server_prompt_queue_thread_safety.py`
  - Doc: `docs/guides/http-server-prompt-queue-thread-safety.md`

- **Verification (socket-free):**
  - `python -m unittest -q tests.test_cli_repl_multiline_paste tests.test_mcp_oauth_callback_pending_thread_safety tests.test_http_server_prompt_queue_thread_safety`
