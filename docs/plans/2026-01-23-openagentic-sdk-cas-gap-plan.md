# Open Agent SDK vs CAS Python API — Gap List + Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 参考 `cladue agent sdk python.md` 的 API 风格，把当前 `openagentic_sdk` 补齐到“可用的 CAS 风格 SDK”：具备 `query()` / “长连接 client” / CAS 消息与 content-block 类型 / 自定义工具（@tool + SDK MCP server）/ 权限与 hooks / 内置工具 I/O 形状对齐（至少覆盖文档列出的工具）。

**Architecture:** 不新增“外部 wrapper 包”（不做 `claude_agent_sdk` 兼容层），直接在 `openagentic_sdk` 内新增/扩展模块与 API：保留现有 event-stream 能力，同时增加 CAS 风格的 Message 输出与 `SDKClient` 会话对象；对工具输入输出做兼容（接受 CAS 字段别名并返回 CAS 风格字段）。

**Tech Stack:** Python 3.11+，纯标准库（`asyncio/dataclasses/typing/json/pathlib/urllib`），复用现有 `openagentic_sdk.runtime/tools/sessions/hooks/permissions/providers`。

---

## 0) 现状快照（当前 `openagentic_sdk` 已有）

- **运行时**：`AgentRuntime` 支持工具循环、session 持久化（events.jsonl）、`resume`、子代理 `Task`、`SkillActivate`。
- **Providers**：`OpenAIProvider`（含 SSE streaming）、`OpenAICompatibleProvider`（现已支持 `complete()` + `stream()`）。
- **Tools**：Read/Write/Edit/Glob/Grep/Bash/WebFetch/WebSearch/SlashCommand/SkillList/SkillLoad/SkillActivate。
- **Permissions**：`PermissionGate(permission_mode=deny/bypass/callback/prompt)`，可交互 approver 与非交互 user_answerer（返回 `UserQuestion` 事件）。
- **Hooks**：PreToolUse/PostToolUse/BeforeModelCall/AfterModelCall/SessionStart/SessionEnd/Stop（自定义接口，不是 CAS 文档的 hook 类型/签名）。
- **Project**：仅 `.claude/skills/**/SKILL.md`、`.claude/commands/*.md`、`CLAUDE.md`（memory）注入索引。

---

## 1) Gap 清单（对照 `cladue agent sdk python.md`）

### A. 顶层 API / 交互模型

- [ ] **CAS 风格 `query()` 输出 Message（content blocks）**：当前 `openagentic_sdk.query()` 输出的是 runtime events（`assistant.delta/tool.use/...`），不是 `AssistantMessage/TextBlock/ResultMessage`。
- [ ] **长连接会话对象（类似 `ClaudeSDKClient`）**：当前只能用 `resume` 手动续聊，没有 `connect/query/receive_response/interrupt/disconnect` 的 client 形态。
- [ ] **prompt 支持 AsyncIterable[dict] streaming input**：当前只支持 `prompt: str`。
- [ ] **interrupts**：当前无中断机制（runtime/provider/tool 侧都没有 abort signal）。

### B. Options/配置（CAS 的 `ClaudeAgentOptions` 风格）

- [ ] **system_prompt / preset**：当前只有 project system prompt（CLAUDE.md/skills/commands 索引），没有显式 `system_prompt` 字段。
- [ ] **include_partial_messages 开关**：当前 streaming provider 会产生 `assistant.delta`，但没有按 options 开关控制 “是否产出 partial/stream 事件”。
- [ ] **max_turns / max_budget_usd / fallback_model / betas / output_format**：当前没有这些字段与行为。
- [ ] **setting_sources=user/project/local + settings precedence**：当前仅 project memory/skills/commands；不支持 `.claude/settings.json`、`.claude/settings.local.json`、`~/.claude/settings.json` 读取与合并。
- [ ] **plugins / sandbox 配置**：当前无插件系统；sandbox 仅“概念缺位”（工具不实现 sandbox）。

### C. 权限系统（CAS PermissionMode + can_use_tool）

- [ ] **PermissionMode**：CAS 的 `"default"|"acceptEdits"|"plan"|"bypassPermissions"`；当前是 `"deny"|"bypass"|"callback"|"prompt"`，语义不对齐。
- [ ] **can_use_tool 回调返回 PermissionResultAllow/Deny（可改 input、可建议 permission updates）**：当前 callback 只返回 bool。
- [ ] **PermissionUpdate / rules / directories**：当前无“权限规则与更新”模型。

### D. Hooks（CAS hook 事件/签名/timeout）

- [ ] **HookEvent 集合**：CAS 有 `PreToolUse/PostToolUse/UserPromptSubmit/Stop/SubagentStop/PreCompact`；当前缺 `UserPromptSubmit/SubagentStop/PreCompact`，且现有 hook 输入/输出结构不一致。
- [ ] **HookMatcher 结构**：CAS matcher 支持 `"Write|Edit"` 之类 + 多个 hook + timeout；当前 matcher 结构不同（单 hook）。

### E. 内置工具 I/O 形状（CAS 文档列出的工具）

下列工具目前“同名但 I/O 不一致”或“缺失”：
- [ ] **Read**：CAS 需 `offset/limit` + 返回带行号 content / 图片 base64；当前仅返回原文本截断。
- [ ] **Write**：CAS 输出要 `message/file_path/bytes_written`；当前无 `message`，且允许 overwrite 控制不同。
- [ ] **Edit**：CAS 输入 `old_string/new_string/replace_all`；当前是 `old/new/count` + anchors（CAS 未提 anchors）。
- [ ] **Bash**：CAS 输入 `timeout(ms)/description/run_in_background`；输出 `output/exitCode/killed/shellId`；当前不支持后台进程管理，字段不同。
- [ ] **Glob**：CAS 输入 `path`（而不是 root），输出包含 `count/search_path` 等；当前仅 root/matches。
- [ ] **Grep**：CAS 支持 modes（content/files_with_matches）+ 上下文；当前只有简单逐行匹配。
- [ ] **WebFetch**：CAS 输入含 `prompt` 且输出 `response/status_code/final_url`；当前只返回 fetched `text`（不做“prompt on content”）。
- [ ] **WebSearch**：CAS 支持 allowed/blocked domains；当前只有 query/max_results。
- [ ] **NotebookEdit**：缺失。
- [ ] **AskUserQuestion（工具）**：当前只有 `UserQuestion` 事件（用于 permissions prompt），没有作为模型可调用 tool 的实现与 I/O。
- [ ] **TodoWrite**：缺失（可做最小实现：写入 session 元数据并发事件）。
- [ ] **BashOutput / KillBash / ExitPlanMode**：缺失（与后台 bash/plan 模式绑定）。
- [ ] **ListMcpResources / ReadMcpResource（工具）**：缺失（MCP 仍是 placeholder）。

### F. MCP + 自定义工具

- [ ] **@tool decorator + create_sdk_mcp_server**：当前无；Options 里虽有 `mcp_servers` placeholder，但 runtime/tools 侧没有实现。
- [ ] **mcp__{server}__{tool} 命名与 allowed_tools 配合**：缺失。

---

## 2) 实施策略（优先级与“今天能交付”的切片）

### P0（今天优先）：让“CAS 风格使用方式”跑起来（不追求 CLI 兼容）

1) **Message 模型 + CAS 风格 query 输出**（在 `openagentic_sdk` 内实现，不新包）
2) **SDKClient：连续会话**（基于 `resume` + session store）
3) **PermissionMode + can_use_tool（最小可用）**
4) **HookEvent 基础对齐（至少 PreToolUse/PostToolUse/UserPromptSubmit/Stop）**
5) **工具 I/O 兼容（Read/Edit/Bash/Write/Glob/Grep）**
6) **AskUserQuestion 作为 tool（用于澄清与 host 交互）**

### P1（后续）：把文档剩余工具补齐

- NotebookEdit、WebFetch(prompt)、WebSearch domain filters、后台 Bash（BashOutput/KillBash）、TodoWrite、（最小）MCP SDK server、自定义工具 decorator。

### P2（暂缓/可能不做）：强 CLI 同构能力

- 插件系统、沙箱完整实现、权限规则持久化与 settings.json 的全部语义（可先做读配置 + 部分字段）。

---

## 3) Implementation Plan（按模块分解 + TDD 验证点）

> 说明：下面每个 Task 先写最小 failing test，再补实现；测试框架沿用仓库现有 `unittest`。

### Task 1: 增加 CAS 风格 Message / ContentBlock 类型（openagentic_sdk 内）

**Files:**
- Create: `openagentic_sdk/messages.py`
- Test: `tests/test_messages_blocks.py`

**Step 1: 写 failing test（类型可构造）**

```python
import unittest
from openagentic_sdk.messages import TextBlock, ToolUseBlock, AssistantMessage

class TestBlocks(unittest.TestCase):
    def test_blocks(self) -> None:
        b = TextBlock(text="hi")
        self.assertEqual(b.text, "hi")
        tu = ToolUseBlock(id="t1", name="Read", input={"file_path": "x"})
        msg = AssistantMessage(content=[tu], model="m")
        self.assertEqual(msg.model, "m")

if __name__ == "__main__":
    unittest.main()
```

Run: `python -m unittest tests/test_messages_blocks.py -q`
Expected: FAIL（模块不存在）→ 然后实现 → PASS。

**Step 2: 实现 dataclasses**

实现最小集合（对齐文档）：`TextBlock/ThinkingBlock/ToolUseBlock/ToolResultBlock` 与 `UserMessage/AssistantMessage/SystemMessage/ResultMessage/StreamEvent`，以及 `Message` union。

---

### Task 2: 新增 `query_messages()`（或为 `query()` 增加 mode）把 runtime events 映射到 Message

**Files:**
- Modify: `openagentic_sdk/api.py`
- Create: `openagentic_sdk/message_query.py`
- Test: `tests/test_query_messages_basic.py`

**Step 1: 写 failing test（能产出 ResultMessage）**

用 FakeProvider（返回固定文本）断言 `ResultMessage` 出现。

**Step 2: 实现 event→message 映射**

最小映射规则：
- `assistant.delta` → 当 options.include_partial_messages=True 时产出 `StreamEvent`（否则忽略 delta）
- `assistant.message` → `AssistantMessage([TextBlock(text)], model=options.model)`
- `tool.use` → `AssistantMessage([ToolUseBlock(...)], model=...)`
- `tool.result` → `AssistantMessage([ToolResultBlock(...)], model=...)`
- `result` → `ResultMessage(subtype="success"|"error", session_id=..., result=final_text, usage=..., ...)`

---

### Task 3: 增加 `SDKClient`（连续会话 API）

**Files:**
- Create: `openagentic_sdk/client.py`
- Modify: `openagentic_sdk/__init__.py`（导出）
- Test: `tests/test_sdk_client_conversation.py`

**Step 1: failing test（两次 query 复用 session_id）**

- client.connect()
- client.query("hi")
- client.receive_response() 消费到 ResultMessage
- 再 client.query("follow up")，断言 session_id 不变（或 resume 生效）

**Step 2: 实现**

client 方法对齐 CAS 文档形态：
- `connect(prompt: str|AsyncIterable[dict]|None=None)`
- `query(prompt: str|AsyncIterable[dict], session_id: str="default")`
- `receive_messages()` / `receive_response()`（消费内部队列，直到 ResultMessage）
- `disconnect()`

注：interrupt 先留 stub（Task 7 再补）。

---

### Task 4: prompt 支持 AsyncIterable[dict]（streaming input）

**Files:**
- Modify: `openagentic_sdk/api.py` / `openagentic_sdk/message_query.py` / `openagentic_sdk/client.py`
- Test: `tests/test_prompt_streaming_input.py`

**Step 1: failing test**

按文档示例：async generator yield `{"type":"text","text":"..."}`，最终拼成完整 prompt 并成功请求。

**Step 2: 实现最小语义**

- 仅支持 `type=="text"`：按顺序拼接（用 `\n` 分隔）
- 其余类型先报 `ValueError`（后续再扩）

---

### Task 5: Permissions 对齐（PermissionMode + can_use_tool 的返回结构）

**Files:**
- Create: `openagentic_sdk/permissions/cas.py`
- Modify: `openagentic_sdk/options.py`
- Modify: `openagentic_sdk/runtime.py`
- Test: `tests/test_permissions_modes.py`

**Step 1: failing test（acceptEdits 自动放行 Edit/Write）**

**Step 2: 实现 PermissionMode**

建议映射：
- `bypassPermissions`：所有工具 auto allow
- `acceptEdits`：Edit/Write auto allow；其余走 prompt/callback（可配置）
- `default`：危险工具（Bash/WebFetch/WebSearch/Write/Edit）走 prompt；只读类（Read/Glob/Grep）默认 allow
- `plan`：拒绝所有 tool（只允许模型输出计划/文本）

**Step 3: can_use_tool 回调**

支持回调返回 `PermissionResultAllow/Deny`：
- allow 可 `updated_input` 覆盖实际 tool input
- deny 可带 message（映射到 ToolResult.error_message），`interrupt=True` 触发 runtime 停止（Task 7 联动）

---

### Task 6: Hooks 对齐（最小：PreToolUse/PostToolUse/UserPromptSubmit/Stop）

**Files:**
- Create: `openagentic_sdk/hooks/cas.py`
- Modify: `openagentic_sdk/runtime.py`
- Test: `tests/test_hooks_user_prompt_submit.py`

**Step 1: failing test（UserPromptSubmit 能改 prompt）**

**Step 2: 实现 CAS HookMatcher 结构与适配**

- 支持 `matcher="Write|Edit"`（复用现有 fnmatch + `|`）
- 支持每个 matcher 多个 hook
- 支持 timeout（`asyncio.wait_for`）
- hook 输入输出按文档 shape（最小字段：session_id/cwd/tool_name/tool_input/prompt）

---

### Task 7: Interrupt（最小可用）

**Files:**
- Modify: `openagentic_sdk/runtime.py`
- Modify: `openagentic_sdk/client.py`
- Test: `tests/test_interrupt_stops_run.py`

**Step 1: failing test（interrupt 后尽快 yield ResultMessage subtype=error/interrupt）**

**Step 2: 实现机制**

- client 内部持有 `asyncio.Event`（abort）
- runtime 在每个 step 与 provider stream loop 中检查 abort
- 若 abort：停止进一步工具执行与模型调用，产出 `Result(stop_reason="interrupted")`

---

### Task 8: 工具 I/O 兼容（不改工具名，支持 CAS 字段别名 + CAS 输出字段）

**Files:**
- Modify: `openagentic_sdk/tools/read.py`
- Modify: `openagentic_sdk/tools/write.py`
- Modify: `openagentic_sdk/tools/edit.py`
- Modify: `openagentic_sdk/tools/bash.py`
- Modify: `openagentic_sdk/tools/glob.py`
- Modify: `openagentic_sdk/tools/grep.py`
- Test: `tests/test_tools_cas_io_compat.py`

**Step 1: failing tests（逐工具）**

覆盖点（按文档）：
- Read: 支持 `offset/limit`，输出 `total_lines/lines_returned`，content 带行号；图片输出 base64（先实现 PNG/JPEG 检测）。
- Edit: 支持 `old_string/new_string/replace_all` 映射到现有 replace；输出 `message/replacements/file_path`。
- Bash: 支持 `timeout(ms)`→秒；输出补 `output/exitCode` 字段（保留旧字段兼容）。
- Glob: `path` 作为 root 别名；输出补 `count/search_path/pattern`。
- Grep: 支持 `mode`（至少 `files_with_matches`），并支持 before/after context。
- Write: 输出补 `message/file_path/bytes_written`，并明确 overwrite 行为（CAS 默认 overwrite？需要你 review 决定）。

---

### Task 9: AskUserQuestion（作为模型可调用 tool）

**Files:**
- Create: `openagentic_sdk/tools/ask_user_question.py`
- Modify: `openagentic_sdk/tools/defaults.py`
- Modify: `openagentic_sdk/runtime.py`（special-case：执行时产出 `UserQuestion` 并等待 user_answerer）
- Test: `tests/test_tool_ask_user_question.py`

**Step 1: failing test**

- FakeProvider 请求调用 `AskUserQuestion`
- runtime 通过 options/user_answerer 返回答案
- tool.result 输出符合文档（answers 映射）

---

### Task 10: 自定义工具（@tool + SDK MCP server 的最小实现）

**Files:**
- Create: `openagentic_sdk/mcp/sdk.py`
- Modify: `openagentic_sdk/options.py`
- Modify: `openagentic_sdk/tools/registry.py` / `openagentic_sdk/tools/openai.py`
- Test: `tests/test_mcp_sdk_tools.py`

**Step 1: failing test**

- 定义 `@tool("add", ...)`，挂到 `create_sdk_mcp_server(name="calc", tools=[add])`
- allowed_tools 包含 `mcp__calc__add`
- FakeProvider 发起 tool_call `mcp__calc__add`
- 断言 tool_result 正确

**Step 2: 实现最小 MCP SDK server**

- 仅支持 `type="sdk"` 的 in-process tools（不实现 stdio/http/sse remote）
- tool schema：支持 “类型映射”与 JSON schema 两种（按文档）

---

### Task 11: NotebookEdit + WebFetch(prompt) + WebSearch domain filters（P1）

**Files:**
- Create: `openagentic_sdk/tools/notebook_edit.py`
- Modify: `openagentic_sdk/tools/web_fetch.py`
- Modify: `openagentic_sdk/tools/web_search_tavily.py`
- Modify: `openagentic_sdk/tools/defaults.py`
- Tests: `tests/test_tools_notebook_edit.py`, `tests/test_web_fetch_prompt.py`, `tests/test_web_search_domain_filters.py`

实现策略（最小可用）：
- NotebookEdit：纯 JSON 操作 `.ipynb`（replace/insert/delete）
- WebFetch：新增 `prompt` 字段；若提供 prompt，则返回 `{response: ...}`（实现方式：先 fetch text，再用 provider.complete 生成简短回答；否则退化为返回 text）
- WebSearch：对结果按 allowed/blocked domains 过滤

---

## 4) 需要你先 review/拍板的“语义选择”

1) **是否允许引入一个“CAS 风格输出 API”而不改现有 `openagentic_sdk.query()`**  
   - 方案 A：保留现有 `query()`（events），新增 `query_messages()`（messages）  
   - 方案 B：`query()` 改为 messages，另提供 `query_events()`（可能影响现有用户/测试）

2) **Write 默认是否允许覆盖？**  
   CAS 文档未明确 overwrite 语义；当前 WriteTool 需要 `overwrite=True` 才能覆盖。

3) **WebFetch(prompt) 是否真的要调用模型？**  
   这会产生额外 token 消耗与网络依赖；也可先返回 fetched text + 由模型自行总结。

4) **MCP remote（stdio/http/sse）是否纳入本期？**  
   本计划 P0/P1 仅做 in-process SDK MCP tools。

