# HTTP Server Prompt Queues: Thread Safety

`OpenAgenticHttpServer` exposes OpenCode-parity endpoints for approvals and user questions:

- `GET /permission` + `POST /permission/{id}/reply`
- `GET /question` + `POST /question/{id}/reply|reject`

These are backed by in-memory “pending” maps and answer queues that are shared across:

- the HTTP handler thread(s)
- background session execution threads (which block waiting for approval/answers)

## Issue

The pending maps and answer-queue maps were plain dicts shared across threads without a lock. Concurrent reads (`list(pending.values())`) and writes could race, causing inconsistent behavior and (rarely) runtime errors.

## Fix

- Introduced `_PromptQueues` (a small lock-guarded helper) to own:
  - pending permission/question records
  - per-request answer queues
- Routed all handler and permission-gate access through this helper.

## Verification

- `python -m unittest -q tests.test_http_server_prompt_queue_thread_safety`

