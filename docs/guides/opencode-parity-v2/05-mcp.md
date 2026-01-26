# v2-05 MCP (Model Context Protocol)

This guide covers configuring MCP servers, authentication, and how MCP tools/prompts/resources surface in the SDK.

## MCP Server Types

MCP servers are configured in `opencode.json` under the `mcp` key.

Supported `type` values:

- `local`: stdio JSON-RPC (spawn a process)
- `remote`: HTTP (StreamableHTTP JSON-RPC) and/or SSE transport

## Local MCP (stdio)

Example:

```json
{
  "mcp": {
    "my_local": {
      "type": "local",
      "command": ["python", "-m", "my_mcp_server"],
      "environment": {
        "MY_TOKEN": "{env:MY_TOKEN}"
      }
    }
  }
}
```

Behavior:

- The server is started on demand.
- Tools are discovered via `tools/list`.
- Prompts and resources are also registered (see below).

## Remote MCP

Example (StreamableHTTP JSON-RPC):

```json
{
  "mcp": {
    "remote": {
      "type": "remote",
      "url": "https://example.com/mcp",
      "headers": {
        "X-Client": "openagentic"
      },
      "oauth": {
        "scope": "mcp:tools"
      }
    }
  }
}
```

Transport notes:

- The SDK tries StreamableHTTP first.
- If the remote endpoint requires auth (401/403), it still treats StreamableHTTP as supported.
- If StreamableHTTP fails for other reasons, it falls back to SSE (`/sse` + `/message` convention).

## OAuth Authentication

OpenCode-style OAuth is supported via the CLI.

Authenticate a server:

```
oa mcp auth remote
```

Manual bearer token mode (skips OAuth):

```
oa mcp auth remote --token "..."
```

Callback server:

- binds to `127.0.0.1`
- default callback URL: `http://127.0.0.1:19876/mcp/oauth/callback`
- you can change the port:

```
oa mcp auth remote --callback-port 19876
```

Token storage:

- OAuth tokens (OpenCode-like) are stored in `OPENAGENTIC_SDK_HOME/mcp/mcp-auth.json` (0600 best-effort).
- Legacy bearer tokens are stored in `OPENAGENTIC_SDK_HOME/mcp/credentials.json`.

Precedence:

- If an OAuth access token exists for the exact server URL, it is preferred over legacy bearer tokens.

## How MCP Surfaces In The Tool System

Tools:

- MCP tools are registered under names like:
  - `mcp__<server>__tool__<toolname>`

Prompts:

- MCP prompts are registered as tools:
  - `mcp__<server>__prompt__<promptname>`

Resources:

- MCP resources are registered as tools:
  - `mcp__<server>__resource__<uri>` (URI is sanitized into a safe identifier)

Tool output format:

- Outputs include both:
  - `text`: concatenated text blocks
  - `content`: the structured MCP `content[]` blocks (best-effort)

## Troubleshooting

- OAuth browser opens but no callback:
  - ensure nothing else is using port 19876
  - check you can reach `http://127.0.0.1:19876/mcp/oauth/callback`

- Remote server requires auth but tools don't show up:
  - run `oa mcp auth <name>` first

- SSE fallback not working:
  - verify the server exposes `{base}/sse` and `{base}/message`
