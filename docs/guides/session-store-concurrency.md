# Session Store Concurrency

## Summary

`openagentic_sdk.sessions.store.FileSessionStore.append_event()` is used in multi-threaded contexts (notably `ThreadingHTTPServer`). Without synchronization, concurrent appends for the same session can race on in-memory sequence assignment and file writes.

## Root Cause

- `append_event()` computed `seq` from a shared `_seq` dict using multiple operations (`get` → maybe `_infer_next_seq` → `+1` → `set`) without a lock.
- It also performed multiple file writes (`events.jsonl` and `transcript.jsonl`) that could overlap between threads.

## Fix

- `FileSessionStore` now maintains a per-session `threading.Lock`.
- `append_event()` acquires the session lock and performs the entire append (seq computation + `events.jsonl` + optional `transcript.jsonl`) under that lock.

## Guarantees

For concurrent calls to `append_event()` targeting the same `session_id`:

- `seq` values are assigned uniquely and in-order.
- `events.jsonl` and `transcript.jsonl` lines are written without interleaving.

## Notes

- Locking is per session id, so different sessions can still append concurrently.
- Reads (`read_events`, `read_metadata`) remain lock-free; they already tolerate missing/partial files by design.

