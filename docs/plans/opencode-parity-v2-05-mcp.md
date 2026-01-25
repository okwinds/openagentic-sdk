# OpenCode Parity v2 — MCP (Transports + OAuth + Prompts/Resources)

## Source of Truth (OpenCode)

- OAuth provider: `/mnt/e/development/opencode/packages/opencode/src/mcp/oauth-provider.ts`
- Auth storage: `/mnt/e/development/opencode/packages/opencode/src/mcp/auth.ts`
- MCP registry/client: `/mnt/e/development/opencode/packages/opencode/src/mcp/index.ts` (and related)
- CLI: `/mnt/e/development/opencode/packages/opencode/src/cli/cmd/mcp.ts`

Additional OpenCode references:

- OAuth callback server: `/mnt/e/development/opencode/packages/opencode/src/mcp/oauth-callback.ts`
- Tool registry integration (MCP prompts/resources/tools are surfaced):
  - `/mnt/e/development/opencode/packages/opencode/src/tool/registry.ts`
  - `/mnt/e/development/opencode/packages/opencode/src/command/index.ts`
  - `/mnt/e/development/opencode/packages/opencode/src/session/prompt.ts`

MCP spec (authoritative, for OAuth + transports):

- Authorization (2025-11-25): https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- Transports (2025-11-25): https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

## OpenCode Behavior (Detailed)

### OAuth

- Uses a fixed local callback endpoint:
  - `http://127.0.0.1:19876/mcp/oauth/callback`
- Callback server behavior:
  - Binds loopback only, fixed port `19876`.
  - Waits up to 5 minutes per OAuth `state`.
  - Rejects requests with missing/unknown state (CSRF guard).
- Supports:
  - dynamic client registration
  - PKCE code verifier storage
  - OAuth state storage
  - token storage with expiry and refresh token
- Validates stored credentials against the MCP server URL (invalid if URL changed).
- Stores everything in a file with `0600` permissions.

Auth flow orchestration (OpenCode):

- `startAuth(name)`:
  - creates callback server
  - generates random `oauthState` (32 bytes hex), stores it
  - creates OAuth provider and attempts connect
  - on unauthorized, captures authorization URL and stores a pending transport
- `authenticate(name)`:
  - calls `startAuth`
  - opens browser to authorization URL
  - waits for callback `code` by matching `state`
  - then calls `finishAuth(name, code)`
- `finishAuth(name, code)`:
  - completes auth on pending transport (`finishAuth(code)`)
  - clears stored code verifier + oauth state
  - reconnects server

References:

- OAuth provider: `oauth-provider.ts`
- Storage: `auth.ts` (file `mcp-auth.json`)

### Registry surfaces

OpenCode surfaces not only tools but also:

- prompts (`prompts/list`, `prompts/get`) integrated into commands
- resources (`resources/list`, `resources/read`)

Naming/sanitization:

- MCP tools become tool IDs of the form `<client>_<tool>` with non `[a-zA-Z0-9_-]` replaced by `_`.
- Prompts become slash commands using `<client>:<prompt>` (again sanitized).

## Current State (openagentic-sdk)

- Remote MCP:
  - StreamableHTTP + SSE fallback: `openagentic_sdk/mcp/remote_client.py`, `openagentic_sdk/mcp/sse_client.py`
  - Bearer token storage: `openagentic_sdk/mcp/credentials.py`
  - OAuth store + flow (new):
    - `openagentic_sdk/mcp/auth_store.py` (mcp-auth.json, 0600)
    - `openagentic_sdk/mcp/oauth_callback.py` (loopback callback server)
    - `openagentic_sdk/mcp/oauth_flow.py` (auth-code + PKCE + DCR + refresh)
- CLI:
  - `oa mcp list/auth/logout`

Gaps vs OpenCode:

- No OAuth flow (PKCE, callback server, dynamic registration).
- Prompts/resources are callable (remote-only) but not parity:
  - local stdio prompts/resources are not registered
  - schemas/arguments for prompts are not modeled
  - content blocks (image/resource) are flattened to text
  - MCP prompts are not exposed as slash commands
- No URL-binding validation for stored credentials.

Status update (this repo):

- Local stdio prompts/resources are now registered as tools.
- URL binding is implemented for OAuth credentials (`serverUrl` match required).
- Tool error propagation to the model is fixed (no more `null` on errors).

Additional correctness gaps (must fix for real parity):

- Error propagation: tool errors currently reach the model as `null` (runtime emits error message but provider messages serialize only `output`).
- SSE resilience: no reconnect/backoff; pending requests may hang on clean disconnect.
- Initialization handshake: current clients jump straight to `tools/list` etc.

Remaining deltas (still not complete parity):

- Automatic interactive OAuth inside the runtime/tool loop (OpenCode surfaces `needs_auth` status and a command; we do the same via CLI `oa mcp auth`, but do not auto-open browser during runtime).
- SSE reconnection/backoff is still not implemented.
- MCP initialize/initialized handshake is still not implemented.

## Plan (No-Compromise Implementation)

- Implement MCP OAuth parity (OpenCode behavior + MCP spec):
  - callback server: `127.0.0.1:19876/mcp/oauth/callback` (5 min state timeout)
  - storage: OpenCode-compatible `mcp-auth.json` semantics (URL binding + chmod 0600)
  - metadata discovery:
    - parse `WWW-Authenticate` and follow RFC 9728 PRM + RFC 8414 AS metadata
    - support path-aware well-known URLs
    - legacy fallbacks where possible
  - PKCE S256 (RFC 7636): code verifier storage + code challenge
  - Dynamic client registration (RFC 7591) when no `clientId` is configured
  - token exchange + refresh token flow
  - attach `Authorization: Bearer ...` to EVERY MCP HTTP request (StreamableHTTP POST, SSE GET/POST)
  - handle 403 `insufficient_scope` with step-up reauth

- Implement prompts/resources parity:
  - register prompts/resources for BOTH remote and local transports
  - preserve MCP `content[]` blocks in tool output (return both `text` and structured `content`)
  - expose MCP prompts as slash commands in the command system (OpenCode-style `client:prompt`)
  - expose MCP resources via the same “file part” semantics where possible (or as structured tool outputs)

- Security:
  - callback server binds to loopback only
  - tokens stored with strict file permissions
  - never log secrets
  - never send access tokens in query params (header only)
  - validate URL binding before using stored tokens
  - prevent tool name collisions (MCP tool IDs are namespaced)

- Tests:
  - OAuth:
    - parse `WWW-Authenticate` (401 + 403) and discover metadata URLs
    - callback server state validation + timeout
    - dynamic client registration + token exchange + refresh
    - storage format + chmod 0600 + URL binding
  - Transports:
    - `Authorization` header attached for StreamableHTTP and SSE
    - reconnect/backoff behavior for SSE; pending requests fail deterministically on disconnect
    - initialize handshake occurs before list/call
  - Surfaces:
    - local prompts/resources registered
    - remote prompt/resource schemas are surfaced
    - MCP prompts appear as slash commands
  - Runtime:
    - tool errors are serialized to the model with message + type (no `null`)
