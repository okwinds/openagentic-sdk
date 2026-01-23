# 项目简要汇报：openagentic

## 一句话概述
这是一个纯 Python、开源的 Agent SDK + CLI，参考 Claude Agent SDK 的编程模型，提供可持久化会话、真实 tool loop（含权限审批）、以及对 `.claude/`（skills / commands / project memory）的磁盘兼容能力。

## 项目目的与背景
- 面向希望获得“完整 agent runtime 体验”的开发者：不仅是 `chat()` 封装，而是可跑通多轮会话、工具调用、权限确认、日志落盘与恢复的最小实现。
- 代码库保持“小而可改”：核心能力尽量用纯 Python 实现，便于二次开发与嵌入业务。
- 兼容 `.claude/` 的工作流习惯：支持从项目目录读取记忆、skills、slash commands，并将索引信息注入 system prompt（CAS 风格）。

## 技术栈与工程形态
- 语言与构建：Python 3.11+；使用 `pyproject.toml` + setuptools；项目依赖列表为空（`dependencies = []`），倾向保持轻量与可移植。
- 包结构：
  - SDK：`openagentic_sdk/`
  - CLI：`openagentic_cli/`
  - 示例：`example/`
  - 测试：`tests/`
- CLI 入口：通过 `pyproject.toml` 的 `project.scripts` 暴露 `oa` 命令（指向 `openagentic_cli.__main__:main`）。

## 核心能力（你能得到什么）
- 最小可用 agent runtime：提供 `run()`（one-shot）、`query()`（流式）、`query_messages()`（CAS 风格）等 API。
- 持久化会话模型：产生 durable `session_id`，落盘 `events.jsonl`，支持 `resume=<session_id>` 恢复。
- 真实 tool loop：模型发起 tool call → 权限门（PermissionGate）决策 → 执行工具 → tool result 回传 → 模型继续生成。
- 人类友好的控制台输出：默认主要打印 assistant 文本；调试模式再输出工具/事件细节。
- `.claude` 兼容：在 `setting_sources=["project"]` 时可索引项目记忆与 skills/commands，并在 system prompt 中维护“Active Skills”，且通过事件持久化（便于 resume 后恢复状态）。

## Provider / 环境变量（默认与常见用法）
- 支持 OpenAI 与 OpenAI-compatible provider。
- 示例与 CLI 默认使用 RIGHTCODE（OpenAI-compatible）：
  - `RIGHTCODE_API_KEY`（必需）
  - `RIGHTCODE_BASE_URL`（可选，默认 `https://www.right.codes/codex/v1`）
  - `RIGHTCODE_MODEL`（可选，默认 `gpt-5.2`）
- `WebSearch`：文档提到使用 Tavily（需要 `TAVILY_API_KEY`）。

## 内置工具（tool registry）
默认包含文件读写/编辑、代码检索、命令执行与联网能力等工具：
- `Read`, `Write`, `Edit`
- `Glob`, `Grep`
- `Bash`
- `WebFetch`
- `WebSearch`
- `TodoWrite`
- `.claude` 相关：`SlashCommand`、`Skill`（以及兼容用 `SkillList/SkillLoad/SkillActivate`）

## CLI 使用方式（面向用户）
- `oa chat`：多轮 REPL（支持 slash commands）
- `oa run "prompt"`：一次性执行（支持流式与 JSON 输出选项）
- `oa resume <session_id>`：恢复会话（等价于 `oa chat --resume <session_id>`）
- `oa logs <session_id>`：汇总 `events.jsonl`，便于快速回顾对话与工具调用
- 会话目录：默认 `~/.openagentic`（可用 `OPENAGENTIC_HOME` 覆盖；兼容旧环境变量 `OPENAGENTIC_SDK_HOME`）

## 现状与成熟度
- 文档标注为早期阶段（API 可能变化），但核心 runtime + tool loop 已可用。

## 可选的下一步（如果你要更深入）
如果你希望进一步了解架构与实现细节，可以在此基础上补充：
- 事件模型（`events.jsonl` 的类型集合与兼容策略）
- 权限模式（PermissionGate 的具体模式与交互/非交互差异）
- `.claude` 索引与 system prompt 拼装策略
- tool schema 的“长描述注入”（opencode 风格）是如何提升调用稳定性的
