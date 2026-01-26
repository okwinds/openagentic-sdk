# Parity 04: Plugins (Hook + Tool Extensions)

Status: implemented (initial slice) in this repo:

- Python plugin loader (file://path, relative path, or importable module)
- Plugin contract: `register(registry)` or `PLUGIN={hooks,tools}`
- Plugins can contribute HookMatchers and Tools
- CLI auto-loads plugins from `opencode.json{,c}` `plugin`/`plugins` array
- Deterministic load order (config order)
- Tests

Key files:

- `openagentic_sdk/plugins.py`
- `openagentic_cli/config.py`
- `tests/test_plugins_loading.py`

## Analysis

OpenCode plugins can:

- Register tools.
- Hook into the runtime.
- Be loaded from local paths or installed packages.

References:

- `opencode/packages/opencode/src/plugin/*`
- Plugin loading: `opencode/packages/opencode/src/config/config.ts`
- Docs: `opencode/packages/web/src/content/docs/plugins.mdx`

Current repo has HookEngine but no plugin packaging/loading.

## Plan

- Define a Python plugin interface (module entrypoints + metadata + hook registration).
- Implement plugin discovery from config and deterministic load order.
- Provide safe sandbox boundaries for plugins.

## TDD

- Tests using a sample plugin under `tests/fixtures/`.
