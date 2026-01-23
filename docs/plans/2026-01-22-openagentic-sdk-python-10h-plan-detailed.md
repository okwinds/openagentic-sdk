# Open Agent SDK (Python) — 10 小时超详细实施计划（v0.1）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal（一句话）**：把当前 `packages/sdk/openagentic-sdk/` 的“能跑的原型”推进到 **可安装、可复现、可扩展、多 Provider、工具齐全、可审计** 的 v0.1（仍然纯 Python，且不依赖 opencode 进程/安装）。

**Architecture（2–3 句）**：保持分层：`runtime`（agent loop）→ `providers`（OpenAI 优先、可扩展）→ `tools`（强内置能力）→ `permissions`（回调+交互审批）→ `hooks`（审计/阻断/改写）→ `sessions`（events.jsonl 落盘 + resume）→ `project`（`.claude` memory/skills/commands）。

**Tech Stack**：Python 3.11+（当前环境 3.12 OK），`asyncio`，标准库优先（`urllib`/`subprocess`/`unittest`），必要时允许 **可选依赖**（但本 10h 计划默认先用 stdlib 保证离线测试可跑）。

---

## 0. 你现在已经有什么（现状盘点，5–10 分钟读完）

当前已有（都在 `packages/sdk/openagentic-sdk/openagentic_sdk/`）：

- 事件模型 + JSON 序列化：`events.py`、`serialization.py`
- Session 落盘（JSONL）：`sessions/store.py`
- 工具系统 + 默认工具集：`tools/*`（含 `Read/Write/Edit/Glob/Grep/Bash/WebFetch/WebSearch(Tavily)/SlashCommand`）
- 权限：`permissions/gate.py`（callback/prompt/bypass/deny）
- Hooks：`hooks/engine.py`（Pre/PostToolUse）
- Provider：`providers/openai.py`（非 streaming，transport 可注入）
- Runtime：`runtime.py` + 对外 `api.py`（`query`/`run`）
- Subagents：`Task` 由 runtime 特判实现，事件带 `parent_tool_use_id`/`agent_name`
- `.claude` 索引：`project/claude.py`（加载 memory/skills/commands）
- OpenAI tool schema 生成：`tools/openai.py`（最小 schema）
- MCP：仅预留字段：`options.py`

现状的关键缺口（按影响排序）：

1) **可安装性**：目前主要靠 `PYTHONPATH=` 跑测试；需要“pip -e”路径打通。  
2) **resume 真正意义**：现在 `resume` 只是复用 session_id，但不会从 events 重建对话/上下文。  
3) **OpenAI streaming**：尚未实现 SSE/增量工具调用拼装。  
4) **权限与交互**：`input()` 直接写死、不可测试、也没 `AskUserQuestion` 语义。  
5) **Hooks 丰富度**：缺少 `BeforeModelCall/AfterModelCall/Stop/SessionStart/SessionEnd` 等关键点；message rewrite 开关需要落地。  
6) **多 Provider 设计**：目前只有 OpenAI；需要把 Provider 扩展到 OpenAI-compatible/Anthropic/Gemini 的最小可测形态（离线 mock）。  
7) **工具“生产级边界”**：Edit 的语义、Bash/Web 输出截断、Web 安全策略、落盘脱敏等需要更明确。  
8) **`.claude` 真正进入 Prompt**：现在只提供 loader；runtime 未把 memory/skill index 注入系统 prompt。  
9) **文档/样例**：需要明确“如何作为 SDK 使用”。

本计划会把 10 小时用在把这些缺口逐个补齐，并给出每一步：要改哪些文件、先写什么 failing test、跑什么命令、预期输出是什么。

---

## 1. 10 小时目标（可验收标准）

**v0.1 结束时，你应该能做到：**

1) `pip install -e packages/sdk/openagentic-sdk` 后，直接 `python -c "import openagentic_sdk"` 成功（无需 PYTHONPATH）
2) 全量单元测试离线通过（含 provider/tool/permissions/hooks/session/runtime/subagents）
3) `query()`：
   - 支持 non-streaming provider（已有）
   - 对 OpenAI provider 支持 streaming（SSE）时能产出 `assistant.delta`
4) `run()` 汇总结果可用：`final_text`、`session_id`、`events`
5) Session：
   - `events.jsonl` 完整落盘
   - `resume=session_id` 能重建消息/工具结果（最小可工作）
6) `.claude`：
   - 能加载 memory + skills index + commands index
   - runtime 能把 memory + skill index 以 system prompt 注入（不内联全部 skill 内容）
   - `/commands` 以 **agent-callable** 方式（`SlashCommand`）工作
7) Permissions：
   - callback 审批（可测试）
   - interactive 审批（可测试：注入输入源，不走真实 stdin）
   - 默认策略有文档（哪些工具“危险”，第一次是否强制 prompt）
8) Hooks：
   - 至少覆盖：PreToolUse / PostToolUse / BeforeModelCall / AfterModelCall / Stop
   - 支持“tool IO rewrite”默认开启、“message rewrite”默认关闭但可开
9) Subagents：
   - `Task` 工具能启动子 runtime
   - 子事件带 `parent_tool_use_id`，并可被父 event stream 透传
   - 子 agent 工具 allowlist 能收紧（测试覆盖）
10) 多 Provider：
   - OpenAI（优先）完善
   - 至少再加 1 个“OpenAI-compatible”（通过 base_url/headers）或“Anthropic 模拟实现”（离线 mock）

---

## 2. 工作方式与节奏（强制约束）

- **粒度**：每个 micro-step 目标 2–5 分钟；一小时完成 10–15 个 micro-step。  
- **测试优先**：每个子任务先写 failing test，再改实现。  
- **离线优先**：任何网络都必须可注入 transport 并在测试里 fake/mocked。  
- **不做 MCP 实现**：只留接口与文档 placeholder。  
- **可审计**：任何 tool 调用、hook 决策、permission 决策都应该能落到 `events.jsonl`（哪怕是最简事件）。  
- **提交策略**：计划里会写“Commit”步骤；你可以按仓库规则执行或跳过（本计划不强制实际提交，但推荐每小时 1–2 个 commit）。

---

## 3. 全局命令（你会反复用到）

### 测试（worktree 根目录）

推荐两种跑法（二选一）：

1) 直接用 PYTHONPATH（无需安装）：

`PYTHONPATH=packages/sdk/openagentic-sdk python3 -m unittest discover -s packages/sdk/openagentic-sdk/tests -p 'test_*.py' -q`

2) 安装后（目标是 Hour 1 结束时可用）：

`python3 -m unittest discover -s packages/sdk/openagentic-sdk/tests -p 'test_*.py' -q`

---

## 4. 10 小时详细拆解（按小时，含 micro-steps）

> 说明：每个小时下面的 Task 都是“可独立推进”的小块；如果某块卡住，先跳到同一小时的下一块，最后再回补。

---

# Hour 1（0:00–1:00）Packaging/可安装性 + 测试入口统一

### Task 1.1：让包能被 pip/editable 安装

**Files:**
- Modify: `packages/sdk/openagentic-sdk/pyproject.toml`
- Create: `packages/sdk/openagentic-sdk/tests/test_install_import.py`

**Step 1（test，fail）**：写 test 确保“未安装时会失败”

```py
# packages/sdk/openagentic-sdk/tests/test_install_import.py
import unittest
class TestInstallImport(unittest.TestCase):
    def test_import_open_agent_sdk(self) -> None:
        import openagentic_sdk  # noqa: F401
```

Run: `python3 -m unittest -q tests/test_install_import.py`
Expected: FAIL (`ModuleNotFoundError`)（在未安装阶段）

**Step 2（impl）**：完善 `pyproject.toml` 的 setuptools 包发现（`[tool.setuptools]` / `packages.find`）

**Step 3（verify）**：安装

Run: `python3 -m pip install -e packages/sdk/openagentic-sdk`
Expected: 成功安装，无需下载（如果环境无网络：确保不引入新依赖）

**Step 4（test，pass）**

Run: `python3 -m unittest discover -s packages/sdk/openagentic-sdk/tests -p 'test_*.py' -q`
Expected: PASS

**Step 5（commit，optional）**

`git add packages/sdk/openagentic-sdk/pyproject.toml packages/sdk/openagentic-sdk/tests/test_install_import.py && git commit -m "feat(openagentic-sdk): make package installable"`

---

### Task 1.2：README 给出“安装/测试/最小 demo”命令

**Files:**
- Modify: `packages/sdk/openagentic-sdk/README.md`

**Step 1（doc）**：补充两套测试命令（PYTHONPATH / 安装后）

**Step 2（doc）**：补充最小示例（使用 FakeProvider 离线跑一轮 tool-loop）

**Step 3（verify）**：`python3 -m py_compile packages/sdk/openagentic-sdk/openagentic_sdk/*.py`
Expected: 无输出

---

### Task 1.3：增加一个 `python -m openagentic_sdk` 的 smoke 入口（可选，但很值）

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/__main__.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_main_smoke.py`

**Step 1（test，fail）**：

`python3 -m openagentic_sdk --help` 期望返回 exit code 0 且打印帮助（用 `subprocess` 测）。

**Step 2（impl）**：实现最小 argparse：
- `--prompt`
- `--provider openai`（暂时只支持 openai/fake）
- `--model`
- `--dry-run`（只打印将要做什么，不调用网络）

**Step 3（test，pass）**

---

# Hour 2（1:00–2:00）事件模型 Contract + 可向后兼容策略

### Task 2.1：事件版本号 + 强约束序列化

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/serialization.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_events_contract.py`

**Step 1（test，fail）**：事件必须：
- JSON object
- `type` 必须存在且是 string
- 未知 type 抛 `UnknownEventTypeError`（自定义异常）

**Step 2（impl）**：
- 新增异常 `openagentic_sdk/errors.py`
- `loads_event`/`event_from_dict` 做明确异常类型

**Step 3（test，pass）**

---

### Task 2.2：事件字段稳定性：为所有事件加 `ts` 与 `seq`

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/events.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/store.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_event_seq.py`

**Step 1（test，fail）**：写 test：每次 append_event 后，events.jsonl 里每行都有递增的 `seq`，并且 `ts` 是 float 时间戳。

**Step 2（impl）**：
- `FileSessionStore` 维护每 session 的 `seq`（可以通过读取最后一行或维护内存 map）
- runtime 发出的每个 event 都补齐 `ts`/`seq`

**Step 3（test，pass）**

---

### Task 2.3：事件“最小可审计字段”补齐（权限/Hook/模型调用）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/events.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_audit_events_present.py`

**Step 1（test，fail）**：
- 工具被拒绝时必须有 `PermissionDecision` 事件（或在 `ToolResult` 中带 `decision="denied"` 也行，但要可区分）
- hook 改写/阻断必须写 HookEvent（已存在，但需要覆盖 BeforeModelCall 等）

**Step 2（impl）**：新增最小事件类型：
- `permission.decision`
- `model.request` / `model.response`（只记录元数据，不落敏感内容，或可配置）

**Step 3（test，pass）**

---

# Hour 3（2:00–3:00）Session：真正 resume + 可复现重建 messages

### Task 3.1：从 events.jsonl 重建 messages（最小可工作）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/store.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_resume_rebuild.py`

**Step 1（test，fail）**：
1) 跑一次 tool-loop（FakeProvider）
2) 拿到 session_id
3) 用 `resume=session_id` 再跑一次 prompt（同 provider），期望第二次 runtime 的 initial messages 包含：
   - 上次用户消息
   - 上次 assistant 输出
   - 上次 tool 结果（作为 tool message）

**Step 2（impl）**：
- 在 session store 增加 `rebuild_messages(session_id) -> list[message]`
- 规则（v0.1 最小）：
  - `AssistantMessage` → `{"role":"assistant","content":...}`
  - `ToolResult` → `{"role":"tool","tool_call_id":..., "content": json.dumps(output)}`
  - 用户消息：需要新增 `UserMessage` 事件或在 runtime 里也落 `user.message`

**Step 3（test，pass）**

---

### Task 3.2：为 resume 增加“只取最近 N 轮”与“截断大输出”

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/options.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/store.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_resume_truncation.py`

**Step 1（test，fail）**：构造大量 events，验证 `resume_max_events` 生效且不会 OOM。

**Step 2（impl）**：在 `OpenAgenticOptions` 增加：
- `resume_max_events: int = 1000`
- `resume_max_bytes: int = ...`

**Step 3（test，pass）**

---

### Task 3.3：父子 session 关联：parent session 可以指到 child session

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/store.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_session_linking.py`

**Step 1（test，fail）**：Task 子代理执行后：
- child session `meta.json` 里写入 parent 信息
- parent session events 有一条 `subagent.link`（或 `ToolResult` output 中带 `child_session_id` + 也落一个 event）

**Step 2（impl）**

**Step 3（test，pass）**

---

# Hour 4（3:00–4:00）Permissions：把 prompt 审批做成可测试模块 + “默认危险工具策略”

### Task 4.1：抽离 interactive 输入源（可注入，unittest 可控）

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/permissions/interactive.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/permissions/gate.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_permissions_prompt.py`

**Step 1（test，fail）**：
- fake input provider 返回 "no" → deny
- fake input provider 返回 "yes" → allow

**Step 2（impl）**：
- `InteractiveApprover(input_fn=...)`
- gate 在 prompt 模式调用它（不直接 `input()`）

**Step 3（test，pass）**

---

### Task 4.2：实现 `AskUserQuestion` 事件/接口（为将来 GUI host 做准备）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/events.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_ask_user_question_event.py`

**Step 1（test，fail）**：当 `permission_mode="prompt"` 且 `interactive=False`：
- runtime 应该 emit 一个 `user.question` 事件而不是直接 deny（由 host 决策）

**Step 2（impl）**：
新增事件 `UserQuestion`：
- `question_id`
- `prompt`
- `choices`
并在 runtime/gate 里支持“host 回答”的 API（v0.1 可先是 callback：`user_answerer(question) -> choice`）

**Step 3（test，pass）**

---

### Task 4.3：默认策略：危险工具第一次必须审批（实现一个 `DefaultApproverPolicy`）

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/permissions/policy.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/options.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_default_policy.py`

**Step 1（test，fail）**：
- `Bash/Edit/Write/WebFetch/WebSearch` 默认标为危险
- `Read/Glob/Grep/SlashCommand` 默认安全

**Step 2（impl）**：
- policy 可缓存 “approve once for this session” 的决定（根据 tool_name + scope）

**Step 3（test，pass）**

---

# Hour 5（4:00–5:00）Hooks：扩展 hook points + message rewrite gate（默认关闭）

### Task 5.1：新增 hook points：BeforeModelCall/AfterModelCall/Stop/SessionStart/SessionEnd

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/hooks/models.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/hooks/engine.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_hooks_model_call.py`

**Step 1（test，fail）**：
- 在 provider 调用前后能看到 hook events
- hook 可以阻断 model call（返回 block）

**Step 2（impl）**：
- `HookEngine.run_before_model_call(...)`
- `HookEngine.run_after_model_call(...)`
- runtime 调用这些 hooks 并落 HookEvent

**Step 3（test，pass）**

---

### Task 5.2：message rewrite hooks（默认关闭，显式开启）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/hooks/engine.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/options.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_hooks_message_rewrite_flag.py`

**Step 1（test，fail）**：当 `enable_message_rewrite_hooks=False`：
- hook 返回 `override_messages` 应被忽略且记录 event（action="ignored")

**Step 2（impl）**：加入严格 gate 与 HookEvent action 标记

**Step 3（test，pass）**

---

### Task 5.3：Hook matcher 支持 `Edit|Write` 这种 “OR” 语法（兼容 CAS 风格）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/hooks/engine.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_hook_matcher_or.py`

**Step 1（test，fail）**：pattern `"Edit|Write"` 对 Edit/Write 命中，对 Read 不命中

**Step 2（impl）**：split by `|`，逐个 fnmatch

**Step 3（test，pass）**

---

# Hour 6（5:00–6:00）Tools：明确语义、边界、截断、原子写、Edit 更安全

### Task 6.1：Write 原子写（temp + rename），并记录 bytes/truncated

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/write.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_write_atomic.py`

**Step 1（test，fail）**：写入过程中模拟异常（可通过写只读目录或 monkeypatch），确保不会产生半写文件

**Step 2（impl）**：写到 `.<name>.tmp` 再 `replace`

**Step 3（test，pass）**

---

### Task 6.2：Edit 从“简单 replace”升级为“定位区间 + 预期上下文”（最小版）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/edit.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_edit_context.py`

**Step 1（test，fail）**：
- 输入包含 `before`/`after` 片段，只有当文件中匹配到该上下文才允许替换

**Step 2（impl）**：实现一个最小“上下文锚点”算法（不需要全 diff）

**Step 3（test，pass）**

---

### Task 6.3：Bash 输出截断标记 + 环境变量控制

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/bash.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_bash_truncation_flags.py`

**Step 1（test，fail）**：输出超过 `max_output_bytes` 时：
- `stdout_truncated=True`

**Step 2（impl）**：输出结构补齐

**Step 3（test，pass）**

---

### Task 6.4：WebFetch 安全策略（私网/localhost/redirect/size/type）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/web_fetch.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_web_fetch_security.py`

**Step 1（test，fail）**：
- 默认拒绝 `http://localhost`
- 默认拒绝 `http://127.0.0.1`
- 允许 `allow_private_networks=True` 时才放行

**Step 2（impl）**：补齐 host 判定（域名解析策略可先不做，v0.1 仅按 hostname/ip 规则）

**Step 3（test，pass）**

---

### Task 6.5：WebSearch Tavily：把“首次必须审批”写进文档 + 工具输出结构稳定

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/web_search_tavily.py`
- Modify: `packages/sdk/openagentic-sdk/README.md`
- Create: `packages/sdk/openagentic-sdk/tests/test_web_search_output_shape.py`

**Step 1（test，fail）**：输出必须有 `results: [{title,url,content,source}]`

**Step 2（impl）**：规范化字段、保证类型

**Step 3（test，pass）**

---

# Hour 7（6:00–7:00）Providers：OpenAI streaming + OpenAI-compatible（第二 provider）

### Task 7.1：OpenAI streaming（SSE）接口

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/providers/openai.py`
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/providers/streaming.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_openai_streaming_sse.py`

**Step 1（test，fail）**：用 fake transport 返回多段 `data: ...\n\n`：
- 文本 delta 事件拼成 `AssistantDelta`
- tool call arguments 分段拼装（必须能组出完整 JSON）

**Step 2（impl）**：
- 新增 `OpenAIProvider.stream(...) -> AsyncIterator[ProviderChunk]`
- chunk 类型至少包含：`text_delta`、`tool_call_delta`、`done`
- 在 provider 内做“tool_call 聚合器”（按 tool_call_id 归并 arguments 字符串）

**Step 3（test，pass）**

---

### Task 7.2：OpenAI-compatible provider（仅 base_url + headers + same protocol）

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/providers/openai_compatible.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_openai_compatible.py`

**Step 1（test，fail）**：用 fake transport 验证：
- base_url 生效
- api_key header 可配置

**Step 2（impl）**：复用 OpenAI provider 逻辑但可注入 header 构造

**Step 3（test，pass）**

---

### Task 7.3：Provider “capabilities” 元数据（是否支持 streaming/tool_calls）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/providers/base.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_provider_capabilities.py`

**Step 1（test，fail）**：runtime 根据 provider 能力选择 `stream` or `complete`

**Step 2（impl）**

**Step 3（test，pass）**

---

# Hour 8（7:00–8:00）Runtime：接入 streaming + 更严谨的 tool schema + 错误恢复

### Task 8.1：runtime 使用 provider.stream 产出 `assistant.delta`

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_runtime_streaming_deltas.py`

**Step 1（test，fail）**：Fake streaming provider 产出 3 个 delta：
- runtime yields 3 个 `assistant.delta`
- 最后 yields `assistant.message` + `result`

**Step 2（impl）**：
- runtime 内部累积 delta 成 message
- 并继续支持 non-streaming

**Step 3（test，pass）**

---

### Task 8.2：tool schema 生成全面化（确保 allowed_tools 生效）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/openai.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_tool_schema_allowlist.py`

**Step 1（test，fail）**：allowed_tools 只允许 Read 时：
- tool schema 只包含 Read（不包含 Bash）

**Step 2（impl）**

**Step 3（test，pass）**

---

### Task 8.3：错误恢复策略：工具失败后是否继续（v0.1 先可配置）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/options.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_runtime_tool_error_policy.py`

**Step 1（test，fail）**：当工具报错：
- policy=stop → runtime 直接 result(stop_reason="tool_error")
- policy=continue → 把错误作为 tool result 回灌模型继续

**Step 2（impl）**

**Step 3（test，pass）**

---

# Hour 9（8:00–9:00）`.claude`：注入 memory + skill index，skills 可运行“路径引导”

### Task 9.1：runtime 在 setting_sources=["project"] 时注入 system messages

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/project/claude.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_runtime_claude_injection.py`

**Step 1（test，fail）**：
- 构造 fixture：CLAUDE.md + skills/commands
- 运行一次 query，FakeProvider 捕获 messages，断言第一条是 system，包含 memory + skills index（名字+路径）

**Step 2（impl）**：
- system content 模板（最小）：
  - memory 段
  - skills index（列表）
  - 指示：需要技能内容时用 `Read` 打开对应 SKILL.md

**Step 3（test，pass）**

---

### Task 9.2：把 commands index 也注入（但不自动展开）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/project/claude.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_runtime_command_index.py`

**Step 1（test，fail）**：system prompt 中包含 commands list（`/hello` → `.claude/commands/hello.md`）

**Step 2（impl）**

**Step 3（test，pass）**

---

### Task 9.3：新增一个 `SkillIndex` 工具（可选，但让 agent 更像 CAS）

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/skill_index.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/defaults.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_skill_index_tool.py`

**Step 1（test，fail）**：给 project_dir，输出 skills 列表（name/path）

**Step 2（impl）**：工具仅返回 index，不返回 SKILL.md 内容

**Step 3（test，pass）**

---

# Hour 10（9:00–10:00）Subagents 深化 + 文档/样例/验收清单

### Task 10.1：子 agent 工具 allowlist 收紧（防止子 agent 滥用 Bash）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/options.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_task_tool_scoping.py`

**Step 1（test，fail）**：
- child agent tools=("Read",) 时，调用 Bash 必须 ToolNotAllowed/PermissionDenied

**Step 2（impl）**：在 child OpenAgenticOptions 构造时强制 allowed_tools=definition.tools

**Step 3（test，pass）**

---

### Task 10.2：给 `Task` 增加并发选项（v0.1 先串行，但接口留好）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/options.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/README.md`（接口说明）

**Step 1（doc）**：`Task` input 预留字段：`concurrency`/`timeout_s`（先不实现并发）

**Step 2（impl）**：解析但忽略（落 HookEvent 或 warning event）

---

### Task 10.3：Examples + 验收 checklist

**Files:**
- Create: `packages/sdk/openagentic-sdk/examples/basic_query.py`
- Create: `packages/sdk/openagentic-sdk/examples/approvals.py`
- Create: `packages/sdk/openagentic-sdk/examples/subagents.py`
- Modify: `packages/sdk/openagentic-sdk/README.md`

**Step 1（impl）**：写 3 个例子（默认用 FakeProvider 离线）

**Step 2（verify）**：

`PYTHONPATH=packages/sdk/openagentic-sdk python3 -m py_compile packages/sdk/openagentic-sdk/examples/*.py`

Expected: 无输出

**Step 3（doc）**：README 加 v0.1 checklist（10 条验收标准）

---

## 5. 最终一键验收（10:00 收尾）

从 worktree 根目录运行：

1)（如果走安装路线）`python3 -m pip install -e packages/sdk/openagentic-sdk`
2) `python3 -m unittest discover -s packages/sdk/openagentic-sdk/tests -p 'test_*.py' -q`
3) `PYTHONPATH=packages/sdk/openagentic-sdk python3 -m py_compile packages/sdk/openagentic-sdk/examples/*.py`

Expected:
- tests 全绿
- examples 语法全绿

---

## 6. 计划之外但必须记录的“后续工作清单”（不计入 10h）

这些建议单独开下一轮（否则 10h 会失控）：

1) MCP 真正实现（stdio/HTTP/SSE + auth）
2) Provider 扩展：Anthropic/Gemini/Bedrock/Vertex/OpenAI Responses API
3) 更强的 diff-based Edit（unified diff，三方 merge 校验）
4) Context summarization（自动摘要 + token budgeting）
5) 安全：WebFetch DNS 解析防 SSRF、Bash sandbox policy、敏感信息自动脱敏
6) 类型检查与格式化（ruff/mypy/pyright）+ CI workflow

