# OpenCode Parity v2 — LSP (Lifecycle + Diagnostics + Navigation)

## Source of Truth (OpenCode)

- LSP orchestration: `/mnt/e/development/opencode/packages/opencode/src/lsp/index.ts`
- Server definitions + install/download behaviors: `/mnt/e/development/opencode/packages/opencode/src/lsp/server.ts`
- Client protocol + diagnostics + open/change notifications: `/mnt/e/development/opencode/packages/opencode/src/lsp/client.ts`

## OpenCode Behavior (Detailed)

### 1) Server registry

- OpenCode ships a built-in registry of LSP servers (typescript, eslint, vue, etc) and can download/build some servers on demand.
- Servers expose:
  - `extensions[]` filter
  - `root(file)` resolver (often "nearest root" by markers)
  - `spawn(root)` returning a process handle and optional initialization settings

References:

- Server registry: `/mnt/e/development/opencode/packages/opencode/src/lsp/server.ts`

### 2) Config overrides

- `cfg.lsp === false` disables all LSPs.
- `cfg.lsp.<name>` can override:
  - disable server
  - extensions
  - command + env
  - initialization

Reference: `/mnt/e/development/opencode/packages/opencode/src/lsp/index.ts`

### 3) Lifecycle + caching

- State is instance-scoped (`Instance.state`).
- Clients are cached per (root, serverID).
- Broken servers are tracked per key and not retried.
- Spawning is deduped with an inflight map.

Reference: `/mnt/e/development/opencode/packages/opencode/src/lsp/index.ts`

### 4) Diagnostics

- Client listens to `textDocument/publishDiagnostics`.
- Maintains a `diagnostics` map keyed by normalized file path.
- Provides `waitForDiagnostics` with debounce.

Reference: `/mnt/e/development/opencode/packages/opencode/src/lsp/client.ts`

### 5) File open/change notifications

- When `notify.open(path)` is called:
  - resolves path
  - reads file content
  - chooses languageId by extension
  - sends `didOpen` or `didChange` depending on tracked version
  - emits watched-files notifications

Reference: `/mnt/e/development/opencode/packages/opencode/src/lsp/client.ts`

## Current State (openagentic-sdk)

Status: PARTIAL

- Implemented:
  - Minimal stdio JSON-RPC LSP client and manager:
    - `openagentic_sdk/lsp/client.py`
    - `openagentic_sdk/lsp/manager.py`
  - Tool surface: `openagentic_sdk/tools/lsp.py`
  - Tests with stub server: `tests/fixtures/lsp_stub_server.py`, `tests/test_lsp_tool.py`

- Missing vs OpenCode:
  - Server registry parity (predefined servers, root resolvers, optional installer/downloader).
  - Config parity for `lsp` section (`cfg.lsp === false`, per-server overrides).
  - Client caching per (root, serverID) and broken-server backoff.
  - Document lifecycle notifications (`didOpen`, `didChange`, watched files).
  - Diagnostics debounce and wait semantics.

## Plan (No-Compromise Implementation)

1) Implement an OpenCode-equivalent LSP registry and config overrides.
2) Add root detection helpers (nearest-root markers).
3) Add document lifecycle notifications and per-file version tracking.
4) Add diagnostics caching and `wait_for_diagnostics` helper.
5) Expand the `lsp` tool surface to match OpenCode operations:
   - diagnostics
   - symbols/workspace symbols
   - definition/references
   - hover

## Security Model

- Spawning language servers is arbitrary execution:
  - must be permission-gated
  - must be opt-in by config
- Any auto-install/downloader must be off by default.

## TDD

- Unit tests:
  - root detection
  - per-file versioning and didOpen/didChange sequencing
- Integration tests:
  - stub server emits diagnostics; client waits with debounce
