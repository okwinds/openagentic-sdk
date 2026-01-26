# Parity 05: Custom Tools (Disk-scanned tools)

Status: implemented (initial slice) in this repo (Python-native):

- Custom tool discovery from on-disk directories:
  - project `.opencode/{tool,tools}/*.py`
  - project `{tool,tools}/*.py`
  - global `${OPENCODE_CONFIG_DIR}/{tool,tools}/*.py` (defaults to `~/.config/opencode`)
- Tool module protocol: `TOOLS = [Tool(), ...]` or `TOOL = Tool()`
- CLI loads and registers discovered tools into the tool registry
- Tests

Key files:

- `openagentic_sdk/custom_tools.py`
- `openagentic_cli/config.py`
- `tests/test_custom_tools_loading.py`

## Analysis

OpenCode can discover tools from config directories (`{tool,tools}/*.{ts,js}`) and merge them into tool registry.

Reference: `opencode/packages/opencode/src/tool/registry.ts`.

Current repo: tools are Python classes in a registry.

## Plan

- Decide and implement a Python-native equivalent:
  - Option A: Python tool scripts (importable modules) from configured roots.
  - Option B: JS/TS tool compatibility layer (requires runtime bridge).
- Add discovery + validation + permission binding.

## TDD

- Tests that load a tool from disk and execute it via runtime tool loop.
