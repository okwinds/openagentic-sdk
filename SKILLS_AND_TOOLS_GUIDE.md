# OpenCode Skills 和 Tools 系统完整指南

> 本文档详细介绍 OpenCode 中 Skills 系统的工作原理、Tool 执行机制以及 Agent 模式下的完整触发流程。

## 目录

1. [命令执行机制](#命令执行机制)
2. [Skill 代码详解](#skill-代码详解)
3. [Agent 模式下 Skill 触发流程](#agent-模式下-skill-触发流程)
4. [数据结构和接口](#数据结构和接口)
5. [权限管理](#权限管理)

---

## 命令执行机制

### 问题：Skills 中如何执行 CMD 命令？

**答案**：通过 **Bash Tool** (`src/tool/bash.ts`) 来执行命令，而不是直接调用 bash 工具。

### 核心架构

#### 1. Bash Tool (`src/tool/bash.ts`)

Bash Tool 是一个通用的命令执行工具，不仅限于 bash，而是根据系统选择合适的 shell：
- **Windows**: cmd 或 PowerShell
- **Unix/Linux/macOS**: bash 或其他 shell

**关键代码**：

```typescript
const shell = Shell.acceptable()  // 根据系统选择合适的 shell
log.info("bash tool using shell", { shell })

const proc = spawn(params.command, {
  shell,
  cwd,
  env: { ...process.env },
  stdio: ["ignore", "pipe", "pipe"],
  detached: process.platform !== "win32",
})
```

#### 2. Tool 定义系统 (`src/tool/tool.ts`)

所有工具都通过 `Tool.define()` 创建：

```typescript
export function define<Parameters extends z.ZodType, Result extends Metadata>(
  id: string,
  init: Info<Parameters, Result>["init"],
): Info<Parameters, Result>
```

**工具结构**：
```typescript
export interface Info<Parameters extends z.ZodType, M extends Metadata> {
  id: string
  init: (ctx?: InitContext) => Promise<{
    description: string
    parameters: Parameters
    execute(args: z.infer<Parameters>, ctx: Context): Promise<{
      title: string
      metadata: M
      output: string
      attachments?: MessageV2.FilePart[]
    }>
  }>
}
```

#### 3. 命令执行参数

**Bash Tool 的参数**：

```typescript
{
  command: z.string(),           // 要执行的命令
  timeout?: z.number(),          // 超时时间（毫秒），默认 2 分钟
  workdir?: z.string(),          // 工作目录
  description: z.string(),       // 命令描述（用于日志和元数据）
}
```

**执行流程**：

```
用户请求 (如："运行 npm install")
    ↓
Tool 系统选择 BashTool
    ↓
BashTool.execute({
  command: "npm install",
  workdir: "/project",
  description: "安装项目依赖"
})
    ↓
权限检查 (ctx.ask)
    ↓
spawn 进程执行命令
    ↓
收集 stdout/stderr
    ↓
超时处理 (DEFAULT_TIMEOUT = 2 * 60 * 1000)
    ↓
返回结果
```

#### 4. Tool 注册 (`src/tool/registry.ts`)

所有工具在应用启动时注册：

```typescript
export namespace ToolRegistry {
  export const state = Instance.state(async () => {
    const custom = [] as Tool.Info[]
    
    // 1. 内置工具
    // - BashTool
    // - EditTool
    // - ReadTool
    // - WriteTool
    // - GlobTool
    // - GrepTool
    // - SkillTool
    // - TaskTool
    // - etc.
    
    // 2. 自定义工具（从 {tool,tools}/*.{js,ts} 加载）
    const glob = new Bun.Glob("{tool,tools}/*.{js,ts}")
    for (const dir of await Config.directories()) {
      for await (const match of glob.scan({ cwd: dir })) {
        const mod = await import(match)
        // 注册自定义工具
      }
    }
    
    // 3. 插件提供的工具
    const plugins = await Plugin.list()
    for (const plugin of plugins) {
      for (const [id, def] of Object.entries(plugin.tool ?? {})) {
        custom.push(fromPlugin(id, def))
      }
    }
    
    return { custom }
  })
}
```

#### 5. 命令执行的关键特性

| 特性 | 实现 |
|------|------|
| **超时控制** | `DEFAULT_TIMEOUT = 2 * 60 * 1000` ms（可通过 flag 配置）|
| **工作目录** | 通过 `workdir` 参数指定，无需 `cd` 命令 |
| **权限管理** | 执行前通过 `ctx.ask()` 请求权限 |
| **输出截断** | 超大输出被截断（MAX_METADATA_LENGTH = 30KB）|
| **中止支持** | 支持 `AbortSignal` 中止执行 |
| **路径解析** | 自动解析命令中的目录和文件路径 |

---

## Skill 代码详解

### Skill 是什么？

**Skill** 是一个包含专门知识和逐步指导的模块化文件，使用 SKILL.md 文件格式定义。

### Skill 系统架构

#### 1. 目录结构

```
项目根目录
├── .opencode/skill/              # 项目级 skills
│   ├── code-review/SKILL.md
│   ├── refactor/SKILL.md
│   └── ...
├── .claude/skills/               # Claude Code 兼容 skills (可选)
│   └── .../SKILL.md
└── ~/.claude/skills/             # 全局 skills (可选)
    └── .../SKILL.md
```

#### 2. SKILL.md 文件格式

```markdown
---
name: code-review
description: 提供代码审查和质量改进建议
---

# 代码审查 Skill

## 目的
当需要审查代码质量时使用此 skill...

## 步骤
1. 第一步...
2. 第二步...

## 最佳实践
- 实践 1
- 实践 2
```

**Frontmatter 必须包含**：
- `name` - skill 唯一标识符
- `description` - 简短描述（显示在 Agent 中）

### 3. Skill 系统源代码

#### `src/skill/skill.ts` - Skill 的发现与管理

```typescript
export namespace Skill {
  // ✅ Skill 的数据结构
  export const Info = z.object({
    name: z.string(),              // skill 名称
    description: z.string(),        // skill 描述
    location: z.string(),           // SKILL.md 文件的绝对路径
  })
  export type Info = z.infer<typeof Info>

  // ✅ 缓存的 skill 列表
  export const state = Instance.state(async () => {
    const skills: Record<string, Info> = {}

    const addSkill = async (match: string) => {
      // 1. 解析 SKILL.md 的 frontmatter + content
      const md = await ConfigMarkdown.parse(match).catch((err) => {
        const message = ConfigMarkdown.FrontmatterError.isInstance(err)
          ? err.data.message
          : `Failed to parse skill ${match}`
        Bus.publish(Session.Event.Error, { error: new NamedError.Unknown({ message }).toObject() })
        log.error("failed to load skill", { skill: match, err })
        return undefined
      })

      if (!md) return

      // 2. 提取 name 和 description
      const parsed = Info.pick({ name: true, description: true }).safeParse(md.data)
      if (!parsed.success) return

      // 3. 检查重复
      if (skills[parsed.data.name]) {
        log.warn("duplicate skill name", {
          name: parsed.data.name,
          existing: skills[parsed.data.name].location,
          duplicate: match,
        })
      }

      // 4. 存储 skill 元数据
      skills[parsed.data.name] = {
        name: parsed.data.name,
        description: parsed.data.description,
        location: match,
      }
    }

    // 扫描 .claude/skills/ (project-level)
    const claudeDirs = await Array.fromAsync(
      Filesystem.up({
        targets: [".claude"],
        start: Instance.directory,
        stop: Instance.worktree,
      }),
    )
    const globalClaude = `${Global.Path.home}/.claude`
    if (await Filesystem.isDir(globalClaude)) {
      claudeDirs.push(globalClaude)
    }

    if (!Flag.OPENCODE_DISABLE_CLAUDE_CODE_SKILLS) {
      for (const dir of claudeDirs) {
        const matches = await Array.fromAsync(
          CLAUDE_SKILL_GLOB.scan({
            cwd: dir,
            absolute: true,
            onlyFiles: true,
            followSymlinks: true,
            dot: true,
          }),
        ).catch((error) => {
          log.error("failed .claude directory scan for skills", { dir, error })
          return []
        })

        for (const match of matches) {
          await addSkill(match)
        }
      }
    }

    // 扫描 .opencode/skill/
    for (const dir of await Config.directories()) {
      for await (const match of OPENCODE_SKILL_GLOB.scan({
        cwd: dir,
        absolute: true,
        onlyFiles: true,
        followSymlinks: true,
      })) {
        await addSkill(match)
      }
    }

    return skills
  })

  // ✅ 获取单个 skill
  export async function get(name: string) {
    return state().then((x) => x[name])
  }

  // ✅ 获取所有 skills
  export async function all() {
    return state().then((x) => Object.values(x))
  }
}
```

**关键点**：
- 使用 `Instance.state()` 创建缓存的状态
- 项目启动时一次性扫描所有 SKILL.md
- 使用 glob 模式发现文件：`{skill,skills}/**/SKILL.md`
- 支持多个数据源：`.claude/`（可选）和 `.opencode/`（必须）

#### `src/tool/skill.ts` - Skill Tool

```typescript
import path from "path"
import z from "zod"
import { Tool } from "./tool"
import { Skill } from "../skill"
import { ConfigMarkdown } from "../config/markdown"
import { PermissionNext } from "../permission/next"

const parameters = z.object({
  name: z.string().describe(
    "The skill identifier from available_skills (e.g., 'code-review' or 'category/helper')"
  ),
})

export const SkillTool = Tool.define("skill", async (ctx) => {
  // ✅ 初始化时加载所有 skills
  const skills = await Skill.all()

  // ✅ 根据 Agent 权限过滤
  const agent = ctx?.agent
  const accessibleSkills = agent
    ? skills.filter((skill) => {
        const rule = PermissionNext.evaluate("skill", skill.name, agent.permission)
        return rule.action !== "deny"
      })
    : skills

  // ✅ 生成动态描述（包含所有可用 skills）
  const description =
    accessibleSkills.length === 0
      ? "Load a skill to get detailed instructions for a specific task. No skills are currently available."
      : [
          "Load a skill to get detailed instructions for a specific task.",
          "Skills provide specialized knowledge and step-by-step guidance.",
          "Use this when a task matches an available skill's description.",
          "<available_skills>",
          ...accessibleSkills.flatMap((skill) => [
            `  <skill>`,
            `    <name>${skill.name}</name>`,
            `    <description>${skill.description}</description>`,
            `  </skill>`,
          ]),
          "</available_skills>",
        ].join(" ")

  return {
    description,
    parameters,
    async execute(params: z.infer<typeof parameters>, ctx) {
      // ✅ 1. 获取 skill 对象
      const skill = await Skill.get(params.name)

      if (!skill) {
        const available = await Skill.all().then((x) => Object.keys(x).join(", "))
        throw new Error(`Skill "${params.name}" not found. Available skills: ${available || "none"}`)
      }

      // ✅ 2. 权限检查
      await ctx.ask({
        permission: "skill",
        patterns: [params.name],
        always: [params.name],
        metadata: {},
      })

      // ✅ 3. 加载并解析 SKILL.md 完整内容
      const parsed = await ConfigMarkdown.parse(skill.location)
      const dir = path.dirname(skill.location)

      // ✅ 4. 格式化返回
      const output = [
        `## Skill: ${skill.name}`,
        "",
        `**Base directory**: ${dir}`,
        "",
        parsed.content.trim(),
      ].join("\n")

      return {
        title: `Loaded skill: ${skill.name}`,
        output,
        metadata: {
          name: skill.name,
          dir,
        },
      }
    },
  }
})
```

### 4. Skill 加载流程

```
应用启动
    ↓
Instance.state() 初始化
    ↓
扫描目录:
├── .claude/skills/    (可选，via flag)
├── ~/.claude/skills/  (全局)
└── .opencode/skill/   (必须)
    ↓
对每个 SKILL.md:
├── ConfigMarkdown.parse()  (解析 frontmatter + content)
├── 提取 name 和 description
├── 检查重复名称 (警告)
└── 存储到 skills 对象
    ↓
缓存完成
    ↓
后续通过 Skill.get(name) 或 Skill.all() 访问
```

### 5. 配置文件解析 (`src/config/markdown.ts`)

```typescript
export namespace ConfigMarkdown {
  export async function parse(filePath: string) {
    // 1. 读取文件
    const raw = await Bun.file(filePath).text()
    
    // 2. 预处理 frontmatter（处理特殊 YAML 格式）
    const template = preprocessFrontmatter(raw)
    
    // 3. 使用 gray-matter 解析
    const md = matter(template)
    
    // 返回 { data: {...}, content: "..." }
    return md
  }
}
```

---

## Agent 模式下 Skill 触发流程

### 完整流程图

```
用户提示 (User Prompt)
    ↓
└─ 解析 @skill_name 标记 (via @语法)
    ↓
创建 User Message
    ↓
SessionPrompt.loop() 主循环
    ↓
1️⃣ resolveTools() - 准备所有可用工具
    ├─ 包括 SkillTool (skill 工具)
    ├─ BashTool (bash 执行工具)
    ├─ EditTool、ReadTool、etc.
    ├─ 权限过滤 (PermissionNext.evaluate)
    └─ 返回 Record<toolName, Tool>
    ↓
2️⃣ LLM.stream() - 调用 LLM 获取响应
    ├─ 传入系统提示词 + 消息历史 + 工具列表
    ├─ LLM 基于上下文决定是否调用 skill tool
    └─ 流式返回 tool-call 事件
    ↓
3️⃣ SessionProcessor.process() - 处理流事件
    ├─ 事件类型: "tool-call"
    ├─ 创建 ToolPart (status: pending → running)
    └─ 触发工具执行
    ↓
4️⃣ Tool.execute() - 执行 SkillTool
    ├─ 参数: { name: "skill-name" }
    ├─ 加载并解析对应的 SKILL.md
    └─ 返回 skill 内容给 Agent
    ↓
5️⃣ 结果保存
    ├─ ToolPart 状态: running → completed
    ├─ 存储 output 和 metadata
    └─ 添加到消息历史
    ↓
6️⃣ Agent 继续循环
    ├─ Skill 内容作为新的上下文
    ├─ 可能调用其他工具
    └─ 或生成文本响应
```

### 详细步骤

#### Step 1: 用户输入解析

**文件**: `src/session/prompt.ts`

```typescript
export async function resolvePromptParts(template: string): Promise<PromptInput["parts"]> {
  const files = ConfigMarkdown.files(template)  // 使用正则 /@\.?[^\s`,.]*/ 解析 @xxx
  
  for (const match of files) {
    const name = match[1]
    
    // 1. 尝试查找是否存在名为 @xxx 的 Agent
    const agent = await Agent.get(name)
    if (agent) {
      parts.push({
        type: "agent",
        name: agent.name,
      })
    }
    
    // 2. 尝试查找是否存在名为 @xxx 的文件
    const filepath = name.startsWith("~/")
      ? path.join(os.homedir(), name.slice(2))
      : path.resolve(Instance.worktree, name)
    
    const stats = await fs.stat(filepath).catch(() => undefined)
    if (stats) {
      parts.push({
        type: "file",
        url: `file://${filepath}`,
        filename: name,
        mime: stats.isDirectory() ? "application/x-directory" : "text/plain",
      })
    }
  }
  
  return parts
}
```

**用户输入示例**：
```
请根据 @code-review skill 审查这个代码
```
→ 解析为：`AgentPart { name: "code-review" }`

#### Step 2: 主循环 - resolveTools()

**文件**: `src/session/prompt.ts#L651`

```typescript
async function resolveTools(input: {
  agent: Agent.Info
  model: Provider.Model
  session: Session.Info
  tools?: Record<string, boolean>
  processor: SessionProcessor.Info
  bypassAgentCheck: boolean
}) {
  const tools: Record<string, AITool> = {}
  const context = (args: any, options: ToolCallOptions): Tool.Context => ({
    sessionID: input.session.id,
    abort: options.abortSignal!,
    messageID: input.processor.message.id,
    callID: options.toolCallId,
    extra: { model: input.model, bypassAgentCheck: input.bypassAgentCheck },
    agent: input.agent.name,
    metadata: async (val: { title?: string; metadata?: any }) => {
      // 更新元数据
    },
    ask: async (req) => {
      // 权限检查
    },
  })

  // ✅ 添加所有内置工具
  const toolRegistry = await ToolRegistry.tools("")
  
  for (const item of toolRegistry) {
    tools[item.id] = {
      description: item.description,
      parameters: item.parameters,
      execute: async (args, options) => {
        // 权限检查
        await Plugin.trigger("tool.execute.before", {...})
        
        // 执行工具
        const result = await item.execute(args, ctx)
        
        // 触发钩子
        await Plugin.trigger("tool.execute.after", {...})
        
        // 返回格式化输出
        return {
          type: "text",
          value: result.output,
        }
      },
    }
  }

  // 类似地添加 MCP tools、Plugin tools 等...

  return tools
}
```

**关键点**：
- `SkillTool.init()` 时会权限过滤
- 生成包含所有可访问 skills 的描述
- 这个描述被发送给 LLM，帮助 LLM 决策

#### Step 3: LLM 调用

**文件**: `src/session/llm.ts#L48`

```typescript
export async function stream(input: StreamInput) {
  // 准备工具列表（包含 skill tool）
  const tools = await resolveTools(input)
  
  // 调用 LLM
  return streamText({
    tools,                           // ← 工具列表（包括 skill）
    activeTools: Object.keys(tools), // ← "skill", "bash", etc.
    messages: input.messages,        // ← 消息历史
    system: input.system,            // ← 系统提示词
    temperature: params.temperature,
    topP: params.topP,
    // ... 其他配置
  })
}
```

**LLM 看到的信息**：
```
可用工具:
- skill: Load a skill to get detailed instructions...
  可用 skills:
  - code-review: 提供代码审查建议
  - refactor: 重构代码建议
  - ...

用户请求: 请根据 code-review skill 审查这个代码
```

LLM 根据此信息决定调用 `skill` 工具，参数为 `{ name: "code-review" }`

#### Step 4: 流处理 - SessionProcessor

**文件**: `src/session/processor.ts#L120`

```typescript
case "tool-call": {
  const match = toolcalls[value.toolCallId]
  if (match) {
    // ✅ 创建或更新 ToolPart
    const part = await Session.updatePart({
      id: toolcalls[value.id]?.id ?? Identifier.ascending("part"),
      messageID: input.assistantMessage.id,
      sessionID: input.assistantMessage.sessionID,
      type: "tool",
      tool: value.toolName,              // "skill"
      callID: value.id,
      state: {
        status: "running",
        input: value.input,              // { name: "code-review" }
        time: { start: Date.now() },
      },
      metadata: value.providerMetadata,
    })
    
    toolcalls[value.toolCallId] = part as MessageV2.ToolPart
  }
}
```

**ToolPart 数据结构**：
```typescript
{
  type: "tool",
  callID: "call-123",
  tool: "skill",
  state: {
    status: "running",
    input: { name: "code-review" },
    time: { start: 1705576800000 },
  },
  metadata: {...},
}
```

#### Step 5: Tool 执行

**文件**: `src/session/prompt.ts#L694`

```typescript
// 在 resolveTools 中，skill tool 的 execute 方法：

async execute(params: { name: string }, ctx) {
  // 1️⃣ 获取 skill 对象
  const skill = await Skill.get("code-review")
  // → { name: "code-review", description: "...", location: "/path/to/SKILL.md" }

  if (!skill) {
    const available = await Skill.all().then((x) => Object.keys(x).join(", "))
    throw new Error(`Skill "${params.name}" not found. Available skills: ${available || "none"}`)
  }

  // 2️⃣ 权限检查
  await ctx.ask({
    permission: "skill",
    patterns: ["code-review"],
    always: ["code-review"],
    metadata: {},
  })
  // 如果用户没有权限，会在这里被询问或拒绝

  // 3️⃣ 加载完整 SKILL.md 内容
  const parsed = await ConfigMarkdown.parse(skill.location)
  // parsed = {
  //   data: { name: "code-review", description: "..." },
  //   content: "# 代码审查 Skill\n\n## 目的\n..."
  // }

  const dir = path.dirname(skill.location)

  // 4️⃣ 格式化返回
  const output = [
    `## Skill: code-review`,
    "",
    `**Base directory**: /path/to/skills`,
    "",
    parsed.content.trim(),
  ].join("\n")

  return {
    title: `Loaded skill: code-review`,
    output,  // ← 完整的 skill 内容
    metadata: {
      name: "code-review",
      dir: "/path/to/skills",
    },
  }
}
```

#### Step 6: 返回结果

**文件**: `src/session/processor.ts#L165`

```typescript
case "tool-result": {
  const match = toolcalls[value.toolCallId]
  if (match && match.state.status === "running") {
    // ✅ 更新 ToolPart 为已完成
    await Session.updatePart({
      ...match,
      state: {
        status: "completed",                    // ← 状态变为完成
        input: value.input,
        output: value.output.output,            // ← skill 的内容
        metadata: value.output.metadata,
        title: value.output.title,
        time: {
          start: match.state.time.start,
          end: Date.now(),
        },
        attachments: value.output.attachments,
      },
    })

    delete toolcalls[value.toolCallId]
  }
}
```

**ToolPart 最终状态**：
```typescript
{
  type: "tool",
  callID: "call-123",
  tool: "skill",
  state: {
    status: "completed",
    input: { name: "code-review" },
    output: "## Skill: code-review\n\n...", // ← 完整内容
    title: "Loaded skill: code-review",
    time: {
      start: 1705576800000,
      end: 1705576801000,
    },
    metadata: { name: "code-review", dir: "..." },
  },
}
```

#### Step 7: 继续循环

Skill 内容被添加到消息历史，Agent 继续处理：

1. **接收 Skill 内容**：作为新的上下文
2. **理解需求**：基于 skill 的指导
3. **调用其他工具**：可能需要 bash、read、edit 等
4. **生成响应**：最终给用户

---

## 数据结构和接口

### Tool 接口

```typescript
namespace Tool {
  // Tool 的上下文信息
  export type Context<M extends Metadata = Metadata> = {
    sessionID: string           // 会话 ID
    messageID: string           // 消息 ID
    agent: string              // Agent 名称
    abort: AbortSignal          // 中止信号
    callID?: string            // 工具调用 ID
    extra?: Record<string, any> // 额外信息
    metadata(input: { title?: string; metadata?: M }): void  // 更新元数据
    ask(input: PermissionRequest): Promise<void>  // 权限请求
  }

  // Tool 定义
  export interface Info<Parameters extends z.ZodType, M extends Metadata> {
    id: string
    init: (ctx?: InitContext) => Promise<{
      description: string
      parameters: Parameters
      execute(args: z.infer<Parameters>, ctx: Context): Promise<{
        title: string
        metadata: M
        output: string
        attachments?: MessageV2.FilePart[]
      }>
      formatValidationError?(error: z.ZodError): string
    }>
  }
}
```

### MessageV2 数据结构

```typescript
namespace MessageV2 {
  // 文本部分
  export const TextPart = PartBase.extend({
    type: z.literal("text"),
    text: z.string(),
    ignored: z.boolean().optional(),
    synthetic: z.boolean().optional(),
  })
  export type TextPart = z.infer<typeof TextPart>

  // Tool 调用部分
  export const ToolPart = PartBase.extend({
    type: z.literal("tool"),
    callID: z.string(),              // 工具调用 ID
    tool: z.string(),                // 工具名称
    state: ToolState,                // 工具状态
    metadata: z.record(z.any()).optional(),
  })
  export type ToolPart = z.infer<typeof ToolPart>

  // Tool 状态
  export const ToolState = z.discriminatedUnion("status", [
    z.object({
      status: z.literal("pending"),
      input: z.record(z.any()),
      raw: z.string(),
    }),
    z.object({
      status: z.literal("running"),
      input: z.record(z.any()),
      time: z.object({ start: z.number() }),
    }),
    z.object({
      status: z.literal("completed"),
      input: z.record(z.any()),
      output: z.string(),
      title: z.string(),
      metadata: z.record(z.any()).optional(),
      time: z.object({ start: z.number(), end: z.number() }),
      attachments: FilePart.array().optional(),
    }),
    z.object({
      status: z.literal("error"),
      error: z.string(),
      time: z.object({ start: z.number(), end: z.number() }),
      metadata: z.record(z.any()).optional(),
      input: z.record(z.any()),
    }),
  ])
  export type ToolState = z.infer<typeof ToolState>
}
```

### LLM StreamInput

```typescript
namespace LLM {
  export type StreamInput = {
    user: MessageV2.User         // 用户消息
    sessionID: string            // 会话 ID
    model: Provider.Model        // 使用的模型
    agent: Agent.Info           // Agent 配置
    system: string[]             // 系统提示词
    abort: AbortSignal           // 中止信号
    messages: ModelMessage[]      // 消息历史
    small?: boolean              // 是否使用小模型
    tools: Record<string, Tool>  // 可用工具
    retries?: number             // 重试次数
  }

  export type StreamOutput = StreamTextResult<ToolSet, unknown>
}
```

---

## 权限管理

### 权限检查流程

#### 1. 初始化时的权限过滤

**文件**: `src/tool/skill.ts`

```typescript
const accessibleSkills = agent
  ? skills.filter((skill) => {
      const rule = PermissionNext.evaluate("skill", skill.name, agent.permission)
      return rule.action !== "deny"  // ← 过滤掉被拒绝的 skills
    })
  : skills
```

#### 2. 执行时的权限请求

**文件**: `src/tool/skill.ts`

```typescript
await ctx.ask({
  permission: "skill",
  patterns: [params.name],      // ← 请求访问特定 skill
  always: [params.name],         // ← 记录允许策略
  metadata: {},
})
// 如果用户没有权限，会在这里被询问或拒绝
```

#### 3. 权限规则配置

```typescript
// Agent 配置示例
{
  name: "code-reviewer",
  permission: [
    {
      permission: "skill",
      action: "allow",
      pattern: "code-review|refactor"  // ← 只允许特定 skills
    },
    {
      permission: "bash",
      action: "deny",                   // ← 禁止执行 bash
      pattern: "*"
    }
  ]
}
```

### PermissionNext 接口

```typescript
namespace PermissionNext {
  // 权限规则
  export interface Rule {
    permission: string
    action: "allow" | "deny"
    pattern: string
  }

  export type Ruleset = Rule[]

  // 评估权限
  export function evaluate(
    permission: string,
    pattern: string,
    ruleset: Ruleset
  ): { action: "allow" | "deny" }

  // 请求权限
  export async function ask(request: Request): Promise<void>

  export interface Request {
    permission: string
    patterns: string[]
    always: string[]
    sessionID: string
    ruleset: Ruleset
    metadata: Record<string, any>
  }
}
```

---

## 总结

### 关键流程

1. **命令执行**：通过 Bash Tool 使用 `spawn()` 执行命令
2. **Skill 发现**：项目启动时扫描 SKILL.md 文件，缓存元数据
3. **Skill 加载**：通过 SkillTool 按需加载完整内容
4. **Agent 触发**：LLM 决定何时调用 skill tool，获取指导内容

### 核心文件

| 文件 | 用途 |
|-----|------|
| `src/tool/bash.ts` | Bash 命令执行工具 |
| `src/tool/tool.ts` | Tool 系统定义 |
| `src/tool/registry.ts` | Tool 注册和管理 |
| `src/skill/skill.ts` | Skill 发现和管理 |
| `src/tool/skill.ts` | Skill Tool（暴露给 Agent） |
| `src/session/prompt.ts` | 会话提示词和主循环 |
| `src/session/llm.ts` | LLM 流调用 |
| `src/session/processor.ts` | 流事件处理 |
| `src/config/markdown.ts` | Markdown 配置解析 |

### 最佳实践

1. **创建 Skill** 时，遵循 frontmatter 规范（name + description）
2. **权限管理** 时，为每个 Agent 配置适当的权限规则
3. **命令执行** 时，使用 `workdir` 而非 `cd` 命令
4. **错误处理** 时，充分利用中止信号和超时机制

---

## 相关资源

- [OpenCode 主文档](../README.md)
- [Agent 配置指南](./AGENTS.md)
- [权限系统文档](./PERMISSION.md)
- [Tool 开发指南](./TOOLS.md)
