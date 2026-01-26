# Parity 07: LSP Integration

## Analysis

OpenCode provides LSP server lifecycle and exposes diagnostics/navigation.

References:

- `opencode/packages/opencode/src/lsp/*`

Current repo has no Python LSP integration.

## Plan

- Implement an LSP manager that can:
  - discover language servers (config-driven)
  - start/stop processes
  - request diagnostics/symbols/definitions
- Expose via:
  - a tool (`LSP`) comparable to OpenCode (gated by permissions)
  - optional CLI status commands

## TDD

- Use a lightweight test server or stub protocol harness for unit tests.
