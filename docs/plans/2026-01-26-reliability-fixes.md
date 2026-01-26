# Reliability Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Fix the highest-risk reliability issues discovered in repo review (session store concurrency, MCP SSE client thread safety, HTTP server invalid JSON handling, WebFetch DNS-rebinding SSRF gap) with TDD + per-fix docs.

**Architecture:** Add minimal synchronization and input-validation at the narrowest boundaries (file append and shared maps). For SSRF, harden hostname handling by validating resolved IPs (with a test-injectable resolver). Each fix gets (1) a focused regression test, (2) minimal production change, (3) a short doc explaining root cause and the chosen mitigation.

**Tech Stack:** Python stdlib (`unittest`, `threading`, `asyncio`, `ipaddress`, `socket`), existing HTTP server + tools.

---

## Task 1: Session Store Concurrency Safety

**Problem:** `FileSessionStore.append_event()` is not thread-safe: it mutates shared `_seq` state and appends to the same file from multiple threads without a lock. This can corrupt JSONL logs or create duplicate/out-of-order seq values.

**Files:**
- Modify: `openagentic_sdk/sessions/store.py`
- Create: `tests/test_session_store_concurrency.py`
- Create doc: `docs/guides/session-store-concurrency.md`

**Step 1: Write the failing test (RED)**

Create `tests/test_session_store_concurrency.py`:

```python
import json
import threading
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path


class TestFileSessionStoreConcurrency(unittest.TestCase):
    def test_concurrent_append_event_produces_valid_jsonl_and_unique_seq(self) -> None:
        from openagentic_sdk.sessions.store import FileSessionStore
        from openagentic_sdk.events import UserMessage

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session(metadata={"title": "t"})

            n_threads = 8
            per_thread = 50

            def worker(tid: int) -> None:
                for i in range(per_thread):
                    store.append_event(sid, UserMessage(text=f"t{tid}:{i}"))

            threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Validate JSONL + seq monotonicity/uniqueness
            events_path = root / "sessions" / sid / "events.jsonl"
            lines = events_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), n_threads * per_thread)
            seqs = []
            for ln in lines:
                obj = json.loads(ln)
                self.assertIsInstance(obj, dict)
                self.assertIsInstance(obj.get("seq"), int)
                seqs.append(obj["seq"])
            self.assertEqual(sorted(seqs), list(range(1, n_threads * per_thread + 1)))
```

**Step 2: Run the test to verify it fails (RED)**

Run: `python -m unittest -q tests.test_session_store_concurrency`

Expected: FAIL (flaky but should fail at least sometimes) due to invalid JSON lines or duplicate/missing `seq`.

**Step 3: Implement minimal locking (GREEN)**

Modify `openagentic_sdk/sessions/store.py` to:
- Introduce a per-session `threading.Lock` (e.g., `_locks: dict[str, threading.Lock]` with lazy initialization).
- Wrap the entire “compute seq + append to events.jsonl + append transcript” in that lock.

**Step 4: Re-run the test (GREEN)**

Run: `python -m unittest -q tests.test_session_store_concurrency`

Expected: PASS reliably (repeat a few times if desired).

**Step 5: Add fix documentation**

Create `docs/guides/session-store-concurrency.md`:
- Root cause summary (multi-threaded server + shared file appends).
- What changed (per-session lock, atomic-ish append).
- Behavioral guarantees (unique seq, JSONL integrity).
- Notes on performance (locks only per-session).

---

## Task 2: MCP `SseMcpClient` Thread Safety

**Problem:** `SseMcpClient`’s `_pending` dict is accessed from the event loop thread and the reader thread; the exception path clears `_pending` from the reader thread which can race with `_request()` adding entries.

**Files:**
- Modify: `openagentic_sdk/mcp/sse_client.py`
- Create: `tests/test_mcp_sse_client_pending_thread_safety.py`
- Create doc: `docs/guides/mcp-sse-client-thread-safety.md`

**Step 1: Write the failing test (RED)**

Create `tests/test_mcp_sse_client_pending_thread_safety.py` (race-repro that doesn’t need a real server):

```python
import asyncio
import threading
import unittest


class TestSseMcpClientPendingThreadSafety(unittest.IsolatedAsyncioTestCase):
    async def test_pending_map_is_safe_under_reader_failure_race(self) -> None:
        from openagentic_sdk.mcp.sse_client import SseMcpClient

        c = SseMcpClient(base_url="http://example.invalid")
        c._loop = asyncio.get_running_loop()  # test-only internal wiring

        # Create a bunch of pending futures while another thread simulates
        # the reader exception-path iterating and clearing.
        stop = threading.Event()
        errors: list[BaseException] = []

        def clearer() -> None:
            try:
                while not stop.is_set():
                    # Simulate the existing exception path: iterate + clear.
                    for _rid, _fut in list(getattr(c, "_pending", {}).items()):
                        pass
                    getattr(c, "_pending", {}).clear()
            except BaseException as e:  # noqa: BLE001
                errors.append(e)

        t = threading.Thread(target=clearer)
        t.start()
        try:
            for _ in range(2000):
                rid = c._next_id
                c._next_id += 1
                fut = asyncio.get_running_loop().create_future()
                c._pending[rid] = fut
                await asyncio.sleep(0)
        finally:
            stop.set()
            t.join(timeout=1.0)

        self.assertEqual(errors, [])
```

**Step 2: Run the test to verify it fails (RED)**

Run: `python -m unittest -q tests.test_mcp_sse_client_pending_thread_safety`

Expected: FAIL intermittently with race-related exceptions (or expose that the code is currently unsafe).

**Step 3: Implement minimal synchronization (GREEN)**

Modify `openagentic_sdk/mcp/sse_client.py` to:
- Add a `threading.Lock` dedicated to `_pending` map operations.
- Ensure all `_pending` reads/writes/clears happen under that lock.
- Keep the “set_result/set_exception” calls scheduled onto the loop thread (`call_soon_threadsafe`) as now.

**Step 4: Re-run the test (GREEN)**

Run: `python -m unittest -q tests.test_mcp_sse_client_pending_thread_safety`

Expected: PASS reliably.

**Step 5: Add fix documentation**

Create `docs/guides/mcp-sse-client-thread-safety.md`:
- Explain the two-thread model (reader thread + loop thread).
- Root cause: shared dict without lock.
- Fix: lock + loop-thread-only future resolution.

---

## Task 3: HTTP Server Returns 400 on Invalid JSON

**Problem:** Server endpoints call `_read_json()` which currently only guards oversize payloads; invalid JSON can raise `json.JSONDecodeError` and result in a 500 instead of a controlled 400.

**Files:**
- Modify: `openagentic_sdk/server/http_server.py`
- Create: `tests/test_http_server_invalid_json_returns_400.py`
- Create doc: `docs/guides/http-server-invalid-json.md`

**Step 1: Write the failing test (RED)**

Create `tests/test_http_server_invalid_json_returns_400.py`:

```python
import json
import unittest
from urllib import request, error


class TestHttpServerInvalidJson(unittest.TestCase):
    def test_append_prompt_rejects_invalid_json(self) -> None:
        from openagentic_sdk.server.http_server import OpenAgenticHttpServer
        from openagentic_sdk.config import build_options

        opts = build_options(cwd=".", project_dir=".", permission_mode="deny", interactive=False)
        srv = OpenAgenticHttpServer(options=opts, host="127.0.0.1", port=0)
        httpd = srv.serve_forever()
        host, port = httpd.server_address[0], int(httpd.server_address[1])
        base = f"http://{host}:{port}"
        try:
            req = request.Request(
                base + "/tui/append-prompt",
                method="POST",
                data=b"{not-json",
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(error.HTTPError) as ctx:
                request.urlopen(req, timeout=5)
            self.assertEqual(ctx.exception.code, 400)
        finally:
            httpd.shutdown()
            httpd.server_close()
```

**Step 2: Run the test to verify it fails (RED)**

Run: `python -m unittest -q tests.test_http_server_invalid_json_returns_400`

Expected: FAIL (likely HTTP 500).

**Step 3: Implement minimal fix (GREEN)**

Modify `openagentic_sdk/server/http_server.py`:
- In `_read_json()`, catch `json.JSONDecodeError` and raise a `ValueError("invalid_json")` (or similar).
- In each endpoint that calls `_read_json()`, map that ValueError to `_write_json(..., 400, {"error": "invalid_json"})`.
  - Keep existing `payload_too_large` handling.

**Step 4: Re-run the test (GREEN)**

Run: `python -m unittest -q tests.test_http_server_invalid_json_returns_400`

Expected: PASS.

**Step 5: Add fix documentation**

Create `docs/guides/http-server-invalid-json.md`:
- Describe which endpoints are affected.
- Document the error contract (`400 {"error":"invalid_json"}`).

---

## Task 4: WebFetch Harden Against DNS-Rebinding (Hostname → Private IP)

**Problem:** `WebFetch` blocks literal private IPs and `localhost`, but does not resolve hostnames; `http://evil.example` resolving to `127.0.0.1` would bypass the check.

**Files:**
- Modify: `openagentic_sdk/tools/web_fetch.py`
- Create: `tests/test_web_fetch_dns_rebinding_block.py`
- Create doc: `docs/guides/webfetch-ssrf-protections.md`

**Step 1: Write the failing test (RED)**

Create `tests/test_web_fetch_dns_rebinding_block.py`:

```python
import unittest


class TestWebFetchDnsRebinding(unittest.TestCase):
    def test_blocks_hostname_resolving_to_private_ip(self) -> None:
        from openagentic_sdk.tools.web_fetch import WebFetchTool
        import openagentic_sdk.tools.web_fetch as wf

        def fake_getaddrinfo(host, port, *args, **kwargs):  # noqa: ANN001,ANN002,ANN003
            return [(None, None, None, None, ("127.0.0.1", 80))]

        old = getattr(wf, "_getaddrinfo", None)
        wf._getaddrinfo = fake_getaddrinfo
        try:
            t = WebFetchTool()
            with self.assertRaises(ValueError) as ctx:
                t._validate_url("http://example.com/")
            self.assertIn("blocked hostname", str(ctx.exception))
        finally:
            wf._getaddrinfo = old
```

**Step 2: Run the test to verify it fails (RED)**

Run: `python -m unittest -q tests.test_web_fetch_dns_rebinding_block`

Expected: FAIL (currently allowed).

**Step 3: Implement minimal fix (GREEN)**

Modify `openagentic_sdk/tools/web_fetch.py`:
- Introduce a module-level `_getaddrinfo = socket.getaddrinfo` indirection for test injection.
- Extend `_is_blocked_host(host)`:
  - If `host` is not a literal IP, resolve via `_getaddrinfo(host, 0)` and block if any resolved address is private/loopback/link-local.
  - Preserve `allow_private_networks` escape hatch.

**Step 4: Re-run the test (GREEN)**

Run: `python -m unittest -q tests.test_web_fetch_dns_rebinding_block`

Expected: PASS.

**Step 5: Add fix documentation**

Create `docs/guides/webfetch-ssrf-protections.md`:
- Explain current protections (scheme + localhost + private IPs + redirects checked per hop).
- Add the hostname-resolution protection and its tradeoffs.
- Note the `allow_private_networks` flag behavior.

---

## Task 5: Verification + Docs Index

**Files:**
- Modify (optional): `docs/guides/README.md` (or nearest index) to link the new docs

**Step 1: Run targeted test suites**

Run:
- `python -m unittest -q tests.test_session_store_concurrency`
- `python -m unittest -q tests.test_mcp_sse_client_pending_thread_safety`
- `python -m unittest -q tests.test_http_server_invalid_json_returns_400`
- `python -m unittest -q tests.test_web_fetch_dns_rebinding_block`

Expected: PASS.

**Step 2: Run full suite**

Run: `python -m unittest -q`

Expected: PASS.

**Step 3: Ensure docs exist for each fix**

Confirm files exist:
- `docs/guides/session-store-concurrency.md`
- `docs/guides/mcp-sse-client-thread-safety.md`
- `docs/guides/http-server-invalid-json.md`
- `docs/guides/webfetch-ssrf-protections.md`

---

## Results (DONE)

Completed on 2026-01-26.

### Implemented Fixes

- **Session store concurrency:** Added per-session locking around sequence assignment and JSONL appends in `FileSessionStore.append_event()`.
  - Code: `openagentic_sdk/sessions/store.py`
  - Test: `tests/test_session_store_concurrency.py`
  - Doc: `docs/guides/session-store-concurrency.md`

- **MCP SSE client thread safety:** Added `_pending_lock` and guarded all `_pending` mutations and reads.
  - Code: `openagentic_sdk/mcp/sse_client.py`
  - Test: `tests/test_mcp_sse_client_pending_thread_safety.py`
  - Doc: `docs/guides/mcp-sse-client-thread-safety.md`

- **HTTP server invalid JSON:** `json.JSONDecodeError` now maps to `400 {"error":"invalid_json"}` consistently via `_read_json_or_write_error()`.
  - Code: `openagentic_sdk/server/http_server.py`
  - Test: `tests/test_http_server_invalid_json_returns_400.py` (uses a fake handler rather than binding a real socket)
  - Doc: `docs/guides/http-server-invalid-json.md`

- **WebFetch DNS rebinding protection:** Hostnames are resolved and blocked if any resolved IP is private/loopback/link-local (when `allow_private_networks=False`).
  - Code: `openagentic_sdk/tools/web_fetch.py`
  - Test: `tests/test_web_fetch_dns_rebinding_block.py`
  - Doc: `docs/guides/webfetch-ssrf-protections.md`

### Verification

- Targeted: `python -m unittest -q tests.test_session_store_concurrency tests.test_mcp_sse_client_pending_thread_safety tests.test_http_server_invalid_json_returns_400 tests.test_web_fetch_dns_rebinding_block`
- Full suite: `python -m unittest -q` (306 tests)
