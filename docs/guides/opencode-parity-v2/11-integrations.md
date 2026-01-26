# v2-11 Integrations (ACP + GitHub + VSCode)

This repo includes a few "integration" entrypoints that are intended to be used by other tools/automations:

- ACP (Agent Client Protocol) over stdio
- GitHub Actions runner helpers
- VSCode extension compatibility endpoints in the local HTTP server

These are best-effort parity with OpenCode.

## ACP (Agent Client Protocol)

Run an ACP v1 server over stdio (NDJSON JSON-RPC):

```
oa acp
```

Notes:

- Transport is newline-delimited JSON-RPC messages on stdin/stdout.
- `stdout` must contain only JSON-RPC messages (logs go to `stderr`).
- Supported methods (minimum): `initialize`, `session/new`, `session/load`, `session/prompt`.
- Supported notifications: `session/update` streaming progress, `session/cancel`.
- Tool approvals are surfaced as server->client requests: `session/request_permission`.

## GitHub Actions

Generate a minimal workflow file:

```
oa github install
```

You can override the output path:

```
oa github install --path .github/workflows/openagentic.yml
```

Run the GitHub worker (typically in Actions):

```
oa github run
```

Local/offline debugging patterns:

- Print the derived prompt and exit:

  `oa github run --print-prompt --event-path /path/to/event.json`

- Use a fixed reply (skips running the agent), useful for testing GitHub API posting:

  `oa github run --reply-text "hi" --event-path /path/to/event.json --token <token> --base-url http://127.0.0.1:1234`

Mention gating:

- For `issue_comment` events, the runner only responds when the comment body contains one of the mention triggers.
- Configure via `MENTIONS` (comma-separated). Default: `/opencode,/oc`.

## VSCode Extension Compatibility

The local HTTP server includes endpoints that the OpenCode VSCode extension probes:

- `GET /app`
- `POST /tui/append-prompt`

Start the server (recommended):

```
oa serve --port 4096
```

Or OpenCode-style alias:

```
oa --port 4096
```
