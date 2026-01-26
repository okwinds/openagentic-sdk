# OpenCode Parity v2-09: LSP

This repo provides an OpenCode-like Language Server Protocol (LSP) tool surface for code intelligence.

## What Works

- Built-in LSP server registry (OpenCode-inspired) with root detection.
- OpenCode-compatible `lsp` config schema with custom-server validation.
- Correct document lifecycle notifications:
  - `workspace/didChangeWatchedFiles`
  - `textDocument/didOpen` (first open)
  - `textDocument/didChange` (subsequent touches)
- Diagnostics collection and a debounced wait helper (`wait_for_diagnostics`).
- Navigation operations (multi-client merge rules):
  - `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy`, `incomingCalls`, `outgoingCalls`
- Server->client JSON-RPC request handling for common methods (e.g. `workspace/configuration`).

## Configuration

OpenCode-style config shape (e.g. `opencode.json`):

```json
{
  "lsp": {
    "pyright": {
      "command": ["pyright-langserver", "--stdio"]
    },
    "custom": {
      "command": ["/path/to/my-lsp", "--stdio"],
      "extensions": [".foo", ".bar"],
      "env": {"FOO": "1"},
      "initialization": {"some": "option"}
    }
  }
}
```

Notes:

- `lsp: false` disables LSP completely.
- Custom server ids must include `extensions` (parity with OpenCode schema validation).

## Security

- Spawning LSP servers is arbitrary execution and is permission-gated by the runtime.
- The `lsp` tool rejects files outside the workspace root (`ToolContext.project_dir` / `ToolContext.cwd`).

## Key Implementation Files

- Registry + root detection: `openagentic_sdk/lsp/registry.py`
- Config parsing/validation: `openagentic_sdk/lsp/config.py`
- Stdio JSON-RPC client: `openagentic_sdk/lsp/client.py`
- Multi-client orchestration: `openagentic_sdk/lsp/manager.py`
- Tool wrapper: `openagentic_sdk/tools/lsp.py`
