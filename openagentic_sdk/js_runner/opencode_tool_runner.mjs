import fs from "fs"
import os from "os"
import path from "path"
import { pathToFileURL } from "url"

function parseArgv(argv) {
  const out = {}
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (!a.startsWith("--")) continue
    const key = a.slice(2)
    const val = argv[i + 1]
    if (val === undefined || val.startsWith("--")) {
      out[key] = true
    } else {
      out[key] = val
      i++
    }
  }
  return out
}

const SHIM_SOURCE = `
class Schema {
  constructor(kind, opts = {}) {
    this.kind = kind
    this.description = opts.description
    this.defaultValue = opts.defaultValue
    this.enumValues = opts.enumValues
    this.item = opts.item
  }

  describe(text) {
    this.description = String(text)
    return this
  }

  default(value) {
    this.defaultValue = value
    return this
  }

  toJSONSchema() {
    let schema = {}
    if (this.kind === "string") schema.type = "string"
    else if (this.kind === "number") schema.type = "number"
    else if (this.kind === "boolean") schema.type = "boolean"
    else if (this.kind === "enum") {
      const vals = Array.isArray(this.enumValues) ? this.enumValues : []
      const typ = typeof vals[0]
      schema.type = typ === "number" ? "number" : "string"
      schema.enum = vals
    } else if (this.kind === "array") {
      schema.type = "array"
      if (this.item && typeof this.item.toJSONSchema === "function") {
        schema.items = this.item.toJSONSchema()
      } else {
        schema.items = {}
      }
    } else {
      schema.type = "object"
    }

    if (typeof this.description === "string" && this.description) schema.description = this.description
    if (this.defaultValue !== undefined) schema.default = this.defaultValue
    return schema
  }
}

export function tool(def) {
  return def
}

tool.schema = {
  string() {
    return new Schema("string")
  },
  number() {
    return new Schema("number")
  },
  boolean() {
    return new Schema("boolean")
  },
  enum(values) {
    return new Schema("enum", { enumValues: Array.isArray(values) ? values : [] })
  },
  array(item) {
    return new Schema("array", { item })
  },
}
`

function escapeModuleString(s) {
  // Embed as a JS string literal.
  return JSON.stringify(String(s))
}

function rewriteSource(originalPath, source) {
  let out = source

  // Rewrite @opencode-ai/plugin import to the local shim.
  out = out.replace(
    /from\s+["']@opencode-ai\/plugin["']([ \t]*;?)/g,
    'from "./__oa_opencode_plugin_shim.mjs"$1',
  )

  // Inline simple text imports: `import X from "./file.txt"`.
  // Note: this intentionally handles the common OpenCode pattern only.
  const baseDir = path.dirname(originalPath)
  out = out.replace(
    /^\s*import\s+([A-Za-z_$][A-Za-z0-9_$]*)\s+from\s+["'](.+?\.txt)["']\s*;?\s*$/gm,
    (m, ident, rel) => {
      const p = path.resolve(baseDir, rel)
      let content = ""
      try {
        content = fs.readFileSync(p, "utf8")
      } catch {
        content = ""
      }
      return `const ${ident} = ${escapeModuleString(content)};`
    },
  )

  return out
}

function buildParametersSchema(argsObj) {
  if (!argsObj || typeof argsObj !== "object" || Array.isArray(argsObj)) {
    return { type: "object", properties: {} }
  }
  const properties = {}
  const required = []
  for (const [key, val] of Object.entries(argsObj)) {
    if (!key) continue
    let js = { type: "string" }
    if (val && typeof val.toJSONSchema === "function") {
      js = val.toJSONSchema()
    }
    properties[key] = js
    if (!Object.prototype.hasOwnProperty.call(js, "default")) required.push(key)
  }
  const out = { type: "object", properties }
  if (required.length) out.required = required
  return out
}

function buildPluginInput(callCtx) {
  const cwd = (callCtx && typeof callCtx.cwd === "string" && callCtx.cwd) || process.cwd()
  const projectDir =
    (callCtx && typeof callCtx.project_dir === "string" && callCtx.project_dir) ||
    (callCtx && typeof callCtx.projectDir === "string" && callCtx.projectDir) ||
    cwd

  // Minimal, safe subset for local tool plugins.
  // If a plugin needs richer OpenCode objects, it won't be compatible yet.
  return {
    client: null,
    project: {},
    worktree: projectDir,
    directory: cwd,
    serverUrl: "",
    $: null,
  }
}

async function main() {
  const args = parseArgv(process.argv.slice(2))
  const mode = args.mode
  const file = args.file
  const exportName = args.export
  const toolId = args["tool-id"]
  const inputArgsRaw = args.args
  const ctxRaw = args.ctx

  if (
    typeof mode !== "string" ||
    !["describe", "execute", "plugin_describe", "plugin_execute"].includes(mode)
  ) {
    throw new Error("--mode must be describe|execute|plugin_describe|plugin_execute")
  }
  if (typeof file !== "string" || !file) {
    throw new Error("--file is required")
  }

  const originalPath = path.resolve(file)
  const src = fs.readFileSync(originalPath, "utf8")

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "oa-opencode-tool-"))
  const toolName = path.basename(originalPath)
  const tmpToolPath = path.join(tmp, toolName)
  const shimPath = path.join(tmp, "__oa_opencode_plugin_shim.mjs")

  // Write shim and rewritten tool module.
  fs.writeFileSync(shimPath, SHIM_SOURCE, "utf8")
  const rewritten = rewriteSource(originalPath, src)
  fs.writeFileSync(tmpToolPath, rewritten, "utf8")

  const mod = await import(pathToFileURL(tmpToolPath).href)

  if (mode === "describe") {
    const exports = []
    for (const [k, v] of Object.entries(mod)) {
      if (!v || typeof v !== "object") continue
      const desc = typeof v.description === "string" ? v.description : ""
      const params = buildParametersSchema(v.args)
      exports.push({ export: k, description: desc, parameters: params })
    }
    console.log(JSON.stringify({ ok: true, exports }))
    return
  }

  if (mode === "plugin_describe") {
    let callCtx = {}
    if (typeof ctxRaw === "string" && ctxRaw.trim()) {
      callCtx = JSON.parse(ctxRaw)
    }
    const input = buildPluginInput(callCtx)
    const tools = []
    const seen = new Set()
    for (const [k, v] of Object.entries(mod)) {
      if (typeof v === "function") {
        if (seen.has(v)) continue
        seen.add(v)
        let hooks = null
        try {
          hooks = await v(input)
        } catch {
          continue
        }
        if (!hooks || typeof hooks !== "object") continue
        const toolMap = hooks.tool
        if (!toolMap || typeof toolMap !== "object") continue
        for (const [id, def] of Object.entries(toolMap)) {
          if (!def || typeof def !== "object") continue
          const desc = typeof def.description === "string" ? def.description : ""
          const params = buildParametersSchema(def.args)
          tools.push({ export: k, toolId: id, description: desc, parameters: params })
        }
        continue
      }
      if (v && typeof v === "object" && v.tool && typeof v.tool === "object") {
        const toolMap = v.tool
        for (const [id, def] of Object.entries(toolMap)) {
          if (!def || typeof def !== "object") continue
          const desc = typeof def.description === "string" ? def.description : ""
          const params = buildParametersSchema(def.args)
          tools.push({ export: k, toolId: id, description: desc, parameters: params })
        }
      }
    }
    console.log(JSON.stringify({ ok: true, tools }))
    return
  }

  // execute
  let callArgs = {}
  if (typeof inputArgsRaw === "string" && inputArgsRaw.trim()) {
    callArgs = JSON.parse(inputArgsRaw)
  }
  let callCtx = {}
  if (typeof ctxRaw === "string" && ctxRaw.trim()) {
    callCtx = JSON.parse(ctxRaw)
  }

  if (mode === "execute") {
    if (typeof exportName !== "string" || !exportName) {
      throw new Error("--export is required for execute")
    }
    const def = mod[exportName]
    if (!def || typeof def.execute !== "function") {
      throw new Error(`export ${exportName} is not a tool definition`)
    }
    const result = await def.execute(callArgs, callCtx)
    console.log(JSON.stringify({ ok: true, result }))
    return
  }

  // plugin_execute
  if (typeof exportName !== "string" || !exportName) {
    throw new Error("--export is required for plugin_execute")
  }
  if (typeof toolId !== "string" || !toolId) {
    throw new Error("--tool-id is required for plugin_execute")
  }
  const pluginExport = mod[exportName]
  let hooks = null
  if (typeof pluginExport === "function") {
    hooks = await pluginExport(buildPluginInput(callCtx))
  } else if (pluginExport && typeof pluginExport === "object") {
    hooks = pluginExport
  }
  if (!hooks || typeof hooks !== "object") {
    throw new Error(`plugin export ${exportName} did not return hooks`)
  }
  const toolMap = hooks.tool
  if (!toolMap || typeof toolMap !== "object") {
    throw new Error(`plugin export ${exportName} has no tool map`)
  }
  const def = toolMap[toolId]
  if (!def || typeof def.execute !== "function") {
    throw new Error(`plugin tool ${toolId} is missing execute()`) 
  }
  const result = await def.execute(callArgs, callCtx)
  console.log(JSON.stringify({ ok: true, result }))
}

main().catch((err) => {
  const e = err instanceof Error ? err : new Error(String(err))
  console.log(JSON.stringify({ ok: false, error: { name: e.name, message: e.message, stack: e.stack } }))
  process.exitCode = 1
})
