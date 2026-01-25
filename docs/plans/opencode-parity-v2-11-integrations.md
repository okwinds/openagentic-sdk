# OpenCode Parity v2 — Integrations (ACP/GitHub/Other Surfaces)

## Source of Truth (OpenCode)

- ACP integration:
  - `/mnt/e/development/opencode/packages/opencode/src/acp/*`
- GitHub action/integration (repo root):
  - `/mnt/e/development/opencode/github/*`

Note: OpenCode does not currently appear to ship a Slack/VSCode integration under `packages/opencode/src` in this checkout; parity should follow what exists in the OpenCode tree.

## Current State (openagentic-sdk)

Status: MISSING / STUB

- Lightweight stubs exist:
  - `openagentic_sdk/integrations/github.py`
  - `openagentic_sdk/integrations/vscode.py`
  - `openagentic_sdk/integrations/slack.py`
  - `openagentic_sdk/integrations/acp.py`

No functional parity implementation is present.

## Plan (No-Compromise Implementation)

1) ACP parity:
  - implement session bridge and any protocol types OpenCode expects
  - add tests that validate the wire format against OpenCode types
2) GitHub parity:
  - implement the equivalent behavior surfaced by `opencode/github/index.ts`
  - provide a Python package/module to run as an action or service

## Security Model

- Integrations usually involve credentials and network access:
  - secrets must be stored securely or passed via env
  - strict redaction in logs
  - least-privilege scopes

## TDD

- Contract tests for message payloads.
- Integration tests using mocked HTTP endpoints.
