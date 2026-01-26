# OpenCode Parity v2-11 — Integrations (ACP + GitHub + Optional Slack/VSCode)

## Source of Truth (OpenCode)

- ACP integration:
  - `/mnt/e/development/opencode/packages/opencode/src/acp/*`
  - ACP CLI entrypoint: `/mnt/e/development/opencode/packages/opencode/src/cli/cmd/acp.ts`
- GitHub action/integration (repo root):
  - `/mnt/e/development/opencode/github/*`
  - GitHub CLI entrypoint (the action runs this): `/mnt/e/development/opencode/packages/opencode/src/cli/cmd/github.ts`
  - GitHub action wrapper: `/mnt/e/development/opencode/github/action.yml`

Optional (product-level, not in packages/opencode/src):

- Slack integration:
  - `/mnt/e/development/opencode/packages/slack/*`
- VSCode extension:
  - `/mnt/e/development/opencode/sdks/vscode/*`

Note: OpenCode's ACP and GitHub integrations are fully implemented in this checkout.
Slack/VSCode exist as separate packages; v2-11 parity will keep those optional and lightweight in this repo.

## Current State (openagentic-sdk)

Status: MISSING / STUB

- Lightweight stubs exist:
  - `openagentic_sdk/integrations/github.py`
  - `openagentic_sdk/integrations/vscode.py`
  - `openagentic_sdk/integrations/slack.py`
  - `openagentic_sdk/integrations/acp.py`

No functional parity implementation is present.

Notably missing:

- No `oa acp` command.
- No `oa github install` / `oa github run` commands.
- No ACP stdio server implementation.
- No GitHub-agent runner implementation.

## Plan (No-Compromise Implementation)

### 1) ACP parity (Agent Client Protocol)

Goal: implement an ACP v1 server that can be launched via stdio (for editors like Zed) and uses this repo's runtime.

OpenCode reference:

- CLI: `/mnt/e/development/opencode/packages/opencode/src/cli/cmd/acp.ts`
- Agent: `/mnt/e/development/opencode/packages/opencode/src/acp/agent.ts`

Protocol requirements (authoritative):

- Method strings: `initialize`, `session/new`, `session/load`, `session/prompt`, `session/cancel`, `session/list`, `session/fork`, `session/resume`, `session/set_model`, `session/set_mode`, `authenticate`.
- Transport: JSON-RPC 2.0 over NDJSON (one JSON object per line) on stdin/stdout.

Implementation steps:

1. Add `oa acp` CLI command that starts an ACP server on stdio.
2. Implement NDJSON JSON-RPC reader/writer with backpressure and graceful shutdown on stdin EOF.
3. Implement required ACP methods:
   - `initialize` -> advertise capabilities matching OpenCode (loadSession=true, embeddedContext/image=true, etc).
   - `session/new` -> create a session and return `sessionId`.
   - `session/prompt` -> run the agent loop; stream updates via `session/update` notifications.
   - `session/cancel` -> abort the active run for that session.
   - `session/load` -> replay transcript/history via `session/update` notifications (and return `null` result allowed).
   - `session/list`/`session/fork`/`session/resume`/`session/set_model`/`session/set_mode` best-effort parity.
4. Implement permission flow parity:
   - When a tool requires approval, send `session/request_permission` to the ACP client and block until a response is received.
5. Implement mapping from openagentic events -> ACP `session/update` union:
   - `assistant.delta` -> `agent_message_chunk`
   - `assistant.message` -> final `agent_message_chunk` with end-of-message semantics
   - tool lifecycle -> `tool_call` + `tool_call_update`
   - todo updates -> `plan`

### 2) GitHub parity (GitHub Action + CLI)

Goal: provide a Python runner that behaves like OpenCode's GitHub agent when invoked in GitHub Actions.

OpenCode reference:

- Action wrapper: `/mnt/e/development/opencode/github/action.yml`
- CLI runner: `/mnt/e/development/opencode/packages/opencode/src/cli/cmd/github.ts`

Implementation steps:

1. Add `oa github install` command:
   - Create `.github/workflows/openagentic.yml` (name TBD) with triggers matching OpenCode:
     - `issue_comment.created`, `pull_request_review_comment.created`, plus optional `workflow_dispatch` and `schedule`.
   - Render the same env/input knobs: `MODEL`, `AGENT`, `SHARE`, `PROMPT`, `USE_GITHUB_TOKEN`, `MENTIONS`, `OIDC_BASE_URL`, plus provider API keys.
2. Add `oa github run` command:
   - Support the same event categories:
     - USER_EVENTS: `issue_comment`, `pull_request_review_comment`, `issues`, `pull_request`.
     - REPO_EVENTS: `schedule`, `workflow_dispatch`.
   - Support mock mode (`--event` JSON, `--token` PAT) for local testing.
   - Implement token acquisition:
     - If `USE_GITHUB_TOKEN=true`: require `GITHUB_TOKEN`.
     - Else: exchange an OIDC token (or PAT in mock mode) via `${OIDC_BASE_URL}/exchange_github_app_token*`.
   - Fetch issue/PR context via GitHub REST + GraphQL (best-effort parity).
   - Create an OpenAgentic session and stream response; on changes:
     - commit + push to branch (new branch for issues; PR branch for PR events)
     - create PR when appropriate.
   - Update comments + reactions with a "working" indicator.

### 3) Optional: Slack + VSCode

We keep `openagentic_sdk/integrations/slack.py` and `openagentic_sdk/integrations/vscode.py` lightweight.
v2-11 parity will document what exists upstream and provide best-effort helpers, but will not attempt to ship a full Slack bot or VSCode extension in this repo.

## Security Model

- Integrations usually involve credentials and network access:
  - secrets must be stored securely or passed via env
  - strict redaction in logs
  - least-privilege scopes

ACP-specific:

- ACP server must never execute tools without going through permission gating.
- ACP `session/request_permission` must redact sensitive tool input where possible.

GitHub-specific:

- Never print tokens.
- Token exchange endpoints must be configurable (`OIDC_BASE_URL`) and default to OpenCode behavior.
- Git operations must not run destructive commands.

## TDD

- Contract tests for message payloads.
- Integration tests using mocked HTTP endpoints.

ACP tests:

- A fake ACP client that speaks NDJSON JSON-RPC, asserts:
  - method names
  - initialize response capability fields
  - session/new -> session/prompt -> streamed session/update notifications
  - session/request_permission roundtrip blocks tool execution until response

GitHub tests:

- Mock GitHub context parsing (issue_comment, pull_request_review_comment, schedule, workflow_dispatch).
- Token exchange mocked via local HTTP server.
- Git operations mocked (do not require network).

## Acceptance Checklist

- `oa acp` starts an ACP v1 server and passes a minimal end-to-end prompt in tests.
- ACP method strings match official SDK (`session/new`, `session/prompt`, etc).
- Permission gating uses `session/request_permission` and honors selected/cancelled outcomes.
- `oa github run` can run in mock mode and produces deterministic prompt construction.
