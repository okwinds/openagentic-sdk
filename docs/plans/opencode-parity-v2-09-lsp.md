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

Concrete notes (OpenCode implementation):

- Built-in server registry is in `packages/opencode/src/lsp/server.ts` and includes (non-exhaustive):
  - `deno`, `typescript`, `vue`, `eslint`, `oxlint`, `biome`
  - `gopls`
  - `ruby-lsp`
  - `ty` (experimental) / `pyright`
  - `elixir-ls`, `zls`
  - `csharp`, `fsharp`, `sourcekit`
  - `rust-analyzer`, `clangd`
  - `svelte`, `astro`
  - `jdtls`, `kotlin`
  - `yaml`, `lua`, `php` (intelephense), `prisma`
  - `dart`, `ocaml`, `bash`, `terraform`
  - `texlab`, `dockerfile`
  - `gleam`, `clojure-lsp`, `nixd`, `tinymist`, `hls`
- Root detection is primarily implemented via a helper:
  - `NearestRoot(includePatterns, excludePatterns?)` (scan upward from file dir to Instance.directory)
  - some servers are "global" and always use `Instance.directory` (e.g. dockerfile)
- Download/install behavior exists for some servers (behind flags):
  - `Flag.OPENCODE_DISABLE_LSP_DOWNLOAD` disables auto-downloads.
  - Some servers install via bun/npm/go/gem or download GitHub archives.

References:

- Server registry: `/mnt/e/development/opencode/packages/opencode/src/lsp/server.ts`

### 2) Config overrides

- `cfg.lsp === false` disables all LSPs.
- `cfg.lsp.<name>` can override:
  - disable server
  - extensions
  - command + env
  - initialization

Concrete schema (OpenCode `config.ts`):

- `lsp: false | Record<string, ({disabled:true} | {command:string[]; extensions?:string[]; disabled?:boolean; env?:Record<string,string>; initialization?:Record<string,any>})>`
- Validation refine: for custom LSP servers (ids not in built-in registry), `extensions` is required.

Reference: `/mnt/e/development/opencode/packages/opencode/src/lsp/index.ts`

### 3) Lifecycle + caching

- State is instance-scoped (`Instance.state`).
- Clients are cached per (root, serverID).
- Broken servers are tracked per key and not retried.
- Spawning is deduped with an inflight map.

Concrete state shape (OpenCode `lsp/index.ts`):

- `servers: Record<string, LSPServer.Info>` (built-ins + config overrides)
- `clients: LSPClient.Info[]`
- `broken: Set<string>` keyed by `root + serverID`
- `spawning: Map<string, Promise<LSPClient.Info | undefined>>` keyed by `root + serverID`

Reference: `/mnt/e/development/opencode/packages/opencode/src/lsp/index.ts`

### 4) Diagnostics

- Client listens to `textDocument/publishDiagnostics`.
- Maintains a `diagnostics` map keyed by normalized file path.
- Provides `waitForDiagnostics` with debounce.

Concrete behavior (OpenCode `lsp/client.ts`):

- `DIAGNOSTICS_DEBOUNCE_MS = 150`.
- `publishDiagnostics` handler:
  - normalize file path (`Filesystem.normalizePath(fileURLToPath(params.uri))`)
  - store diagnostics array
  - special-case: if diagnostics are first seen for a file and `serverID === "typescript"`, do not emit the diagnostics event.
- `waitForDiagnostics({path})`:
  - subscribe to diagnostics events for same `path` and `serverID`
  - debounce 150ms (to allow semantic diagnostics after syntax)
  - timeout after 3000ms and resolve anyway

Reference: `/mnt/e/development/opencode/packages/opencode/src/lsp/client.ts`

### 5) File open/change notifications

- When `notify.open(path)` is called:
  - resolves path
  - reads file content
  - chooses languageId by extension
  - sends `didOpen` or `didChange` depending on tracked version
  - emits watched-files notifications

Concrete behavior (OpenCode `lsp/client.ts`):

- Tracks `files[path] -> version` (0-based).
- On first open:
  - send `workspace/didChangeWatchedFiles` with `type: 1` (Created)
  - clear diagnostics for that path
  - send `textDocument/didOpen` with `version: 0` and full text
- On subsequent opens:
  - send `workspace/didChangeWatchedFiles` with `type: 2` (Changed)
  - increment version
  - send `textDocument/didChange` with `contentChanges: [{text}]`

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
  - Correct handling of server->client JSON-RPC requests (OpenCode handles workspace/configuration, workDoneProgress, etc).
  - Multi-client merge semantics (OpenCode queries ALL matching clients and flattens results).

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

Concrete parity checklist (v2-09):

- Registry:
  - Built-in servers exist (ids/extensions/root markers) even when `cfg.lsp` is unset.
  - Config overrides can disable built-ins, override extensions, and override spawn command/env/init.
  - Custom servers require `extensions` (schema parity).
- Manager:
  - Selects ALL servers that match the file extension.
  - Computes per-server root (NearestRoot patterns), caches clients per `(root, serverID)`.
  - Tracks broken keys and does not retry.
  - Dedupes concurrent spawns with an inflight map.
- Client:
  - Implements initialize capabilities comparable to OpenCode.
  - Handles `workspace/configuration` and common server->client requests.
  - Implements `notify.open()` with didOpen/didChange + didChangeWatchedFiles.
  - Stores diagnostics per normalized file path.
  - Implements `wait_for_diagnostics` with debounce + timeout.
- Tool:
  - Verifies availability via `hasClients(file)` before touching.
  - Calls `touchFile(file, waitForDiagnostics=true)` before operations.
  - For operations, queries ALL matching clients and flattens/filters results.

## Security Model

- Spawning language servers is arbitrary execution:
  - must be permission-gated
  - must be opt-in by config
- Any auto-install/downloader must be off by default.

Security notes for Python implementation:

- Treat the `lsp` tool as non-safe by default (so PermissionGate default mode prompts).
- Do not auto-download language servers unless an explicit flag is enabled.
- Never send absolute paths outside the workspace root; validate file paths.
- Ensure LSP subprocesses are cleaned up on shutdown to avoid leaking background processes.

## TDD

- Unit tests:
  - root detection
  - per-file versioning and didOpen/didChange sequencing
- Integration tests:
  - stub server emits diagnostics; client waits with debounce
