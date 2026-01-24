# Parity 06: MCP Full (Transports + OAuth + Tool/Prompt/Resource Registry)

Status: implemented (initial slice) in this repo:

- Local MCP servers over stdio with LSP-style `Content-Length` framing
- Remote MCP servers over simple JSON-RPC over HTTP POST (test harness)
- Tool discovery (`tools/list`) and invocation (`tools/call`) mapped to tools named `mcp__<server>__<tool>`
- Tools registered into the runtime tool registry before first model call
- Tests for both local and remote transports

Key files:

- `openagentic_sdk/mcp/client.py`
- `openagentic_sdk/mcp/http_client.py`
- `openagentic_sdk/mcp/wrappers.py`
- `openagentic_sdk/runtime.py`
- `tests/test_mcp_local_tools.py`
- `tests/test_mcp_remote_tools.py`

Remaining parity items (not done yet):

- SSE / StreamableHTTP transport compatibility with MCP reference implementations
- OAuth flows + credential storage + CLI UX

## Analysis

OpenCode has full MCP support:

- Local and remote servers (SSE/HTTP transports).
- OAuth flows for remote servers.
- Tool/prompt/resource listing and invocation.

References:

- `opencode/packages/opencode/src/mcp/index.ts`
- OAuth: `opencode/packages/opencode/src/mcp/oauth-provider.ts`
- CLI: `opencode/packages/opencode/src/cli/cmd/mcp.ts`

Current repo: only in-process "SDK MCP" wrapper exists: `openagentic_sdk/mcp/sdk.py`.

## Plan

- Implement MCP client with:
  - transport abstractions (local process stdio, remote SSE/HTTP)
  - registry of tools/prompts/resources
  - tool invocation mapping to OpenAI/Responses function-calling schemas
- Implement OAuth credential storage and flow hooks.
- Integrate into `OpenAgenticOptions` and CLI.

## TDD

- Use a test MCP server fixture to validate listing + invocation.
