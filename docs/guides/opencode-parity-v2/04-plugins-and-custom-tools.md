# v2-04 Plugins + Custom Tools

This guide explains how to extend the SDK with plugins and custom tools.

## Concepts

- A *tool* is something the model can call (Read, Bash, MCP tools, etc).
- A *plugin* can contribute:
  - additional tools
  - hooks (intercept model calls, inject prompt context, etc)

This repo supports both Python-based extensions and OpenCode-style JS/TS tool modules.

## Python Custom Tools

Put Python tools in any of these locations:

- Project pack: `.opencode/tool/*.py` or `.opencode/tools/*.py`
- Project root: `tool/*.py` or `tools/*.py`
- Global config: `${OPENCODE_CONFIG_DIR}/tool/*.py` or `${OPENCODE_CONFIG_DIR}/tools/*.py`

They are discovered at startup by the CLI and registered into the tool registry.

## JS/TS Custom Tools (OpenCode Style)

OpenCode tools are JS/TS modules. This repo can run them via `bun` in a subprocess.

Discovery locations:

- `.opencode/tool/*.{js,ts}` and `.opencode/tools/*.{js,ts}`
- `tool/*.{js,ts}` and `tools/*.{js,ts}`
- `${OPENCODE_CONFIG_DIR}/{tool,tools}/*.{js,ts}`

Naming rules (matches OpenCode):

- file `hello.ts` default export => tool id `hello`
- file `hello.ts` named export `extra` => tool id `hello_extra`

Enablement (disabled by default for safety):

- `opencode.json`: `experimental.js_tools: true`
- or env: `OA_ENABLE_JS_TOOLS=1`

Minimal example (`.opencode/tools/hello.ts`):

```ts
import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "Say hello",
  args: {
    name: tool.schema.string().default("world"),
  },
  async execute(args) {
    return `hello ${args.name}`
  },
})
```

Notes:

- No dependency auto-install is performed.
- If the tool imports third-party packages, you must install them yourself.
- A minimal compatibility shim for `@opencode-ai/plugin` is provided by the runner.

## Python Plugins

Configure plugins via `opencode.json`:

```json
{
  "plugin": [
    "file://.opencode/plugins/my_plugin.py"
  ]
}
```

A Python plugin can export either:

- `register(registry)`
- or `PLUGIN = { hooks, tools }`

Plugins can add hook matchers and tool instances.

## JS/TS Plugins Contributing Tools

This repo also supports a limited OpenCode-style JS/TS plugin surface:

- Only `file://...` plugin specs are supported.
- Plugins can contribute `hooks.tool` (a tool map).

Enablement (disabled by default):

- `opencode.json`: `experimental.js_plugins: true`
- or env: `OA_ENABLE_JS_PLUGINS=1`

Example (`opencode.json`):

```json
{
  "experimental": { "js_plugins": true },
  "plugin": ["file://.opencode/plugins/my_plugin.ts"]
}
```

Example plugin (`.opencode/plugins/my_plugin.ts`):

```ts
import { tool } from "@opencode-ai/plugin"

export default async function plugin(_input) {
  return {
    tool: {
      plugin_add: tool({
        description: "Add two numbers",
        args: { a: tool.schema.number().default(1), b: tool.schema.number().default(2) },
        async execute(args) {
          return args.a + args.b
        },
      }),
    },
  }
}
```

## Security Notes

- JS/TS tools/plugins run arbitrary code. Keep them disabled unless you trust the source.
- Tool modules are imported (top-level code executes). Avoid side effects at import time.
- Prefer running the server on loopback + auth when tools are enabled.
