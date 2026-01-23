# Open Agent SDK (Python) — 10 小时“超细化”实施计划（v0.1）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 10 小时内，把 `packages/sdk/openagentic-sdk/` 从“能跑的原型”推进到 **可安装（pip -e）**、**强工具能力**、**skills 体系可用**、**hooks/permissions 完整可审计**、**sessions 可 resume**、**OpenAI 优先且支持 streaming**、并具备“多 Provider 扩展骨架”的 v0.1。

**Architecture:** 保持分层：`api(query/run)` → `runtime(agent loop)` → `providers` → `tools` → `permissions` → `hooks` → `sessions` → `project(.claude)`；并引入 `skills` 子系统：`.claude/skills/**/SKILL.md` 的索引、加载、激活（active skill）与测试套件（离线、可复现）。

**Tech Stack:** Python 3.11+（当前 3.12 OK），`asyncio`，标准库优先（`urllib`, `subprocess`, `unittest`），所有网络行为必须通过“可注入 transport”在测试中模拟；不实现 MCP（仅保留 API + 文档占位）。

---

## 0. 总时间预算（600 分钟）

> 每个 micro-step 目标 2–5 分钟；每小时 10–20 个 micro-step。遇到卡点：先跳过，记录 TODO，继续推进后续可并行部分。

| Hour | 主题 | 目标产出（可验收） |
|------|------|--------------------|
| 1 | Packaging | `pip install -e` 后无需 PYTHONPATH 跑 tests |
| 2 | Events Contract | 事件有 version/seq/ts，未知 type 明确错误 |
| 3 | Sessions/Resume | `resume=session_id` 重建 messages（最小可用） |
| 4 | Permissions UX | prompt 审批可测试 + AskUserQuestion 事件模型 |
| 5 | Hooks 扩展 | model hooks + message rewrite gate（默认关） |
| 6 | Tools 边界 | Edit/Write/Bash/Web 安全与截断明确、可测 |
| 7 | Providers | OpenAI streaming（SSE）+ OpenAI-compatible 第二 provider |
| 8 | Runtime 流式 | runtime 产出 assistant.delta + tool_call 聚合 |
| 9 | Skills 核心 | `.claude` skills index/加载/激活 + 执行语义 |
| 10 | Skills 测试套件 | skills e2e fixtures、合规/回归测试、docs/examples |

---

## 1. 统一跑法（你会反复用到）

### 1.1 未安装（开发态）跑测试

Run（worktree 根目录）：

`PYTHONPATH=packages/sdk/openagentic-sdk python3 -m unittest discover -s packages/sdk/openagentic-sdk/tests -p 'test_*.py' -q`

Expected：PASS

### 1.2 安装后跑测试（Hour 1 结束时必须成立）

Run（worktree 根目录）：

1) `python3 -m pip install -e packages/sdk/openagentic-sdk`
2) `python3 -m unittest discover -s packages/sdk/openagentic-sdk/tests -p 'test_*.py' -q`

Expected：PASS（无需 PYTHONPATH）

---

## 2. Skills：我们要的“可用”到底是什么（核心定义）

> 这里把“skills 是重点”定义清楚，否则会在实现中不断扩大范围。

### 2.1 v0.1 skills 必须具备的能力

1) **发现（Discovery）**：扫描 `.claude/skills/**/SKILL.md`，产出索引（name/path/summary）。
2) **加载（Load）**：提供工具 `SkillLoad`（或 `SkillUse`）把某个 skill 内容读出来（并可解析出结构化“checklist”）。
3) **激活（Activate）**：允许 runtime 维护“当前激活的 skills 列表”，并在每次 model call 的 system prompt 里提示“active skills”。
4) **执行（Execution）**：SDK 本身不“自动执行”skill（避免 DSL 失控），但要通过：
   - system prompt 模板
   - 工具 surface（SkillList/SkillLoad）
   - hooks（可选）  
   让模型有足够信息去“按照 skill 的流程”调用工具（Read/Grep/Edit/Bash/Web…）。
5) **可测试（Testability）**：提供一套 fixtures + fake provider，让测试能覆盖：
   - skills 的索引/加载/解析
   - runtime 注入 skill index + active skill
   - “模型按 skill 指示调用工具”的最小端到端循环（不走网络）

### 2.2 v0.1 skills 明确不做（避免爆炸）

- 不实现“技能 DSL 自动执行”（例如 SKILL.md 里写 RUN: Bash … 就自动跑）。
- 不实现 MCP-based skills（仅 API 占位）。
- 不实现复杂的“强制合规”证明（比如必须先调用某技能，否则拒绝执行全部工具）；只做可选 hook/策略。

---

## 3. 详细计划（按小时，细到 micro-step）

> 下面每个 Task 都严格写：Files / Step 1 failing test / Step 2 run & fail / Step 3 minimal impl / Step 4 run & pass / Step 5 commit（可选）。

---

# Hour 1（0:00–1:00）Packaging：可安装 + 测试入口统一

## Task 1.1：让包能被 pip -e 安装（不靠 PYTHONPATH）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/pyproject.toml`
- Create: `packages/sdk/openagentic-sdk/tests/test_install_import.py`

**Step 1: 写 failing test（在“未安装”时预期会失败）**

`packages/sdk/openagentic-sdk/tests/test_install_import.py`

```py
import unittest


class TestInstallImport(unittest.TestCase):
    def test_import_open_agent_sdk(self) -> None:
        import openagentic_sdk  # noqa: F401


if __name__ == "__main__":
    unittest.main()
```

**Step 2: 运行，确认当前失败**

Workdir: `packages/sdk/openagentic-sdk`
Run: `python3 -m unittest -q tests/test_install_import.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'openagentic_sdk'`

**Step 3: 修改 packaging 配置（最小可行）**

目标：让 setuptools 能发现包 `openagentic_sdk`。

在 `packages/sdk/openagentic-sdk/pyproject.toml` 添加（示例）：

```toml
[tool.setuptools]
package-dir = {"" = "."}

[tool.setuptools.packages.find]
where = ["."]
include = ["openagentic_sdk*"]
```

**Step 4: 安装并验证 test 通过**

Workdir: repo root
Run: `python3 -m pip install -e packages/sdk/openagentic-sdk`
Expected: 安装成功

Run: `python3 -m unittest discover -s packages/sdk/openagentic-sdk/tests -p 'test_*.py' -q`
Expected: PASS

**Step 5: Commit（可选）**

```bash
git add packages/sdk/openagentic-sdk/pyproject.toml packages/sdk/openagentic-sdk/tests/test_install_import.py
git commit -m "feat(openagentic-sdk): support editable install"
```

---

## Task 1.2：让 `python -m unittest` 在包目录内也能跑

**Files:**
- Modify: `packages/sdk/openagentic-sdk/tests/test_imports.py`
- Create: `packages/sdk/openagentic-sdk/tests/__init__.py`

**Step 1: failing test**

在 `packages/sdk/openagentic-sdk` 目录执行：
Run: `python3 -m unittest -q`
Expected: 目前可能出现“发现不到 tests”或 import 路径问题

**Step 2: 实现**

- 添加 `packages/sdk/openagentic-sdk/tests/__init__.py`（空文件即可）
- 确保 `unittest discover` 能在 `packages/sdk/openagentic-sdk/tests` 找到全部 tests

**Step 3: 验证**

Workdir: `packages/sdk/openagentic-sdk`
Run: `python3 -m unittest discover -s tests -p 'test_*.py' -q`
Expected: PASS

---

## Task 1.3：增加 `__main__`（CLI smoke，离线）

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/__main__.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_main_help.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_main_help.py`

```py
import subprocess
import sys
import unittest


class TestMainHelp(unittest.TestCase):
    def test_help(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "openagentic_sdk", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("openagentic-sdk", (proc.stdout + proc.stderr).lower())


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Workdir: repo root
Run: `python3 -m unittest -q packages/sdk/openagentic-sdk/tests/test_main_help.py`
Expected: FAIL（模块不存在）

**Step 3: minimal impl**

`packages/sdk/openagentic-sdk/openagentic_sdk/__main__.py`

```py
import argparse

def main() -> int:
    p = argparse.ArgumentParser(prog="openagentic-sdk")
    p.add_argument("--help", action="help", help="show help")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 4: run & pass**

Run: `python3 -m unittest -q packages/sdk/openagentic-sdk/tests/test_main_help.py`
Expected: PASS

---

# Hour 2（1:00–2:00）Events Contract：版本/seq/ts + 明确错误类型

## Task 2.1：新增 errors 模块 + UnknownEventTypeError

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/errors.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/serialization.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_unknown_event_type.py`

**Step 1: failing test**

```py
import unittest

from openagentic_sdk.serialization import loads_event
from openagentic_sdk.errors import UnknownEventTypeError


class TestUnknownEventType(unittest.TestCase):
    def test_unknown_type(self) -> None:
        with self.assertRaises(UnknownEventTypeError):
            loads_event('{"type":"nope"}')


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Run: `python3 -m unittest -q packages/sdk/openagentic-sdk/tests/test_unknown_event_type.py`
Expected: FAIL（没有 UnknownEventTypeError）

**Step 3: minimal impl**

- 在 `errors.py` 定义：
  - `class OpenAgentSdkError(Exception): ...`
  - `class UnknownEventTypeError(OpenAgentSdkError): ...`
  - `class InvalidEventError(OpenAgentSdkError): ...`
- 在 `serialization.py` 将 ValueError 替换为这些异常

**Step 4: run & pass**

---

## Task 2.2：为所有 events 增加 `ts` 与 `seq`（可审计）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/events.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/store.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_event_seq_ts.py`

**Step 1: failing test（写入 session 后检查 jsonl）**

`packages/sdk/openagentic-sdk/tests/test_event_seq_ts.py`

```py
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.events import SystemInit
from openagentic_sdk.sessions.store import FileSessionStore


class TestEventSeqTs(unittest.TestCase):
    def test_events_have_seq_and_ts_in_jsonl(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session()

            store.append_event(sid, SystemInit(session_id=sid, cwd="/x", sdk_version="0.0.0"))
            store.append_event(sid, SystemInit(session_id=sid, cwd="/y", sdk_version="0.0.0"))

            p = root / "sessions" / sid / "events.jsonl"
            lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2)
            o1 = json.loads(lines[0])
            o2 = json.loads(lines[1])
            # seq: strictly increasing integers starting from 1
            self.assertIsInstance(o1.get("seq"), int)
            self.assertIsInstance(o2.get("seq"), int)
            self.assertEqual(o1["seq"], 1)
            self.assertEqual(o2["seq"], 2)
            # ts: float epoch seconds
            self.assertIsInstance(o1.get("ts"), (int, float))
            self.assertIsInstance(o2.get("ts"), (int, float))
            self.assertLessEqual(o1["ts"], o2["ts"])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Run: `python3 -m unittest -q packages/sdk/openagentic-sdk/tests/test_event_seq_ts.py`
Expected: FAIL（当前 events 没有 seq/ts）

**Step 3: minimal impl（最小变更策略）**

目标：不让每个 event 都显式填 ts/seq（太麻烦），而是 **在落盘前统一注入**：

- `FileSessionStore.append_event(...)` 写盘前把 event 转成 dict，然后加上：
  - `seq`：每个 session 自增 int
  - `ts`：`time.time()` float

实现建议：

1) `FileSessionStore` 增加一个私有 map：`_seq: dict[str,int]`（session_id → last seq）
2) `append_event`：
   - `seq = _seq.get(session_id, 0) + 1`
   - `_seq[session_id] = seq`
   - `obj = event_to_dict(event)`（来自 `serialization.py`）
   - `obj["seq"]=seq; obj["ts"]=time.time()`
   - `json.dumps(obj)` 写入 jsonl
3) `read_events`：
   - `loads_event` 应忽略 `seq/ts`（不在 dataclass 字段内），或我们把 `EventBase` 增加 `seq/ts` 字段（更一致）

建议 v0.1 走“字段进入事件模型”的路线（更一致）：

- `EventBase` 增加：
  - `ts: float | None = None`
  - `seq: int | None = None`
- `event_from_dict` / dataclass 构造会接收这些字段（无需特殊忽略）

**Step 4: run & pass**

Run: `python3 -m unittest -q packages/sdk/openagentic-sdk/tests/test_event_seq_ts.py`
Expected: PASS

---

## Task 2.3：新增 `UserMessage` 事件（为 resume 重建 messages 铺路）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/events.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/serialization.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_user_message_event.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_user_message_event.py`

```py
import unittest
from openagentic_sdk.events import UserMessage
from openagentic_sdk.serialization import dumps_event, loads_event


class TestUserMessageEvent(unittest.TestCase):
    def test_roundtrip(self) -> None:
        e1 = UserMessage(text="hi")
        raw = dumps_event(e1)
        e2 = loads_event(raw)
        self.assertEqual(e2, e1)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Run: `python3 -m unittest -q packages/sdk/openagentic-sdk/tests/test_user_message_event.py`
Expected: FAIL（无 UserMessage）

**Step 3: minimal impl**

- `events.py` 增加：
  - `UserMessage(type="user.message", text=..., parent_tool_use_id?, agent_name?)`
- `serialization.py` 的 `_TYPE_MAP` 加入 `"user.message": UserMessage`
- `runtime.query()` 在建立 messages 时，把用户 prompt 落一个 `UserMessage` 事件到 session

**Step 4: run & pass**

---

## Task 2.4：明确事件兼容策略（文档 + 1 个 contract test）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/README.md`
- Create: `packages/sdk/openagentic-sdk/tests/test_event_backward_compat.py`

**Step 1: failing test**

规则：未来新增字段不得破坏旧事件解析；旧 jsonl 里多出来的未知字段要能被忽略/容忍。

在测试中构造：

```py
raw = '{"type":"assistant.message","text":"x","new_field":123}'
```

`loads_event(raw)` 仍应成功（忽略 `new_field`）。

**Step 2: impl**

如果我们继续用 dataclass 直接 `cls(**kwargs)`，会因未知字段报错。解决：

- `event_from_dict` 在构造前，用 `inspect.signature(cls)` 过滤只保留参数里存在的 keys（dataclass 的字段名）。

**Step 3: pass**

---

# Hour 5（4:00–5:00）Hooks：扩展 hook points + message rewrite gate（默认关闭）

## Task 5.1：新增 hook points：SessionStart/SessionEnd/BeforeModelCall/AfterModelCall/Stop

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/hooks/models.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/hooks/engine.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_hooks_model_points.py`

**Step 1: failing test（完整代码）**

`packages/sdk/openagentic-sdk/tests/test_hooks_model_points.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.hooks.engine import HookEngine
from openagentic_sdk.hooks.models import HookDecision, HookMatcher
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.sessions.store import FileSessionStore


class NoopProvider:
    name = "noop"
    def __init__(self) -> None:
        self.calls = 0
    async def complete(self, *, model, messages, tools=(), api_key=None):
        self.calls += 1
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestHooksModelPoints(unittest.IsolatedAsyncioTestCase):
    async def test_before_model_hook_can_block(self) -> None:
        async def block(_input):
            return HookDecision(block=True, block_reason="nope", action="block")

        hooks = HookEngine(before_model_call=[HookMatcher(name="block", tool_name_pattern="*", hook=block)])

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgenticOptions(
                provider=NoopProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
                hooks=hooks,
            )
            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="hi", options=options):
                events.append(e)
                if getattr(e, "type", None) == "result":
                    break
            # Expect a result with stop_reason indicating blocked model call
            r = next(e for e in events if getattr(e, "type", None) == "result")
            self.assertIn("blocked", (r.stop_reason or "").lower())


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（HookEngine 没有 before_model_call）

**Step 3: minimal impl**

1) `hooks/models.py`：
- `HookMatcher` 不再绑定 tool_name_pattern（对 model hooks 更通用），改成：
  - `matcher: str`（例如 `"*"` 或 `"Edit|Write"`）
  - `kind: Literal["tool","model","session","stop"]`
  - `hook: HookCallback`

但为了最小改动，也可以先“复用现有 HookMatcher”，新加 list 字段：
- `before_model_call: Sequence[HookMatcher] = ()`
- `after_model_call: Sequence[HookMatcher] = ()`
- `session_start: Sequence[HookMatcher] = ()`
- `session_end: Sequence[HookMatcher] = ()`
- `stop: Sequence[HookMatcher] = ()`

2) `hooks/engine.py` 增加方法：
- `run_before_model_call(messages, context) -> (messages, hook_events, decision?)`
- `run_after_model_call(output, context) -> (output, hook_events, decision?)`
- `run_session_start(context)` / `run_session_end(context)`
- `run_stop(final_text, context)`

3) `runtime.py` 调用顺序：
- session_start hooks（创建 session 后、发 SystemInit 前后都可以，但需统一）
- before_model_call hooks（在 provider.complete/stream 前）
- after_model_call hooks（在 provider 返回后）
- stop hooks（产出 Result 前）
- session_end hooks（退出前）

4) Block 语义：
- BeforeModelCall block → 直接 yield Result(stop_reason="blocked:before_model_call") 并结束

**Step 4: run & pass**

---

## Task 5.2：message rewrite hooks 默认关闭（显式开启）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/hooks/engine.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/options.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_hooks_message_rewrite_flag.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_hooks_message_rewrite_flag.py`

```py
import unittest

from openagentic_sdk.hooks.engine import HookEngine
from openagentic_sdk.hooks.models import HookDecision, HookMatcher


class TestMessageRewriteFlag(unittest.IsolatedAsyncioTestCase):
    async def test_override_messages_ignored_when_flag_off(self) -> None:
        async def rewrite(_input):
            return HookDecision(override_messages=[{"role": "system", "content": "x"}], action="rewrite_messages")

        engine = HookEngine(before_model_call=[HookMatcher(name="rw", tool_name_pattern="*", hook=rewrite)], enable_message_rewrite_hooks=False)
        msgs, events, decision = await engine.run_before_model_call(messages=[{"role": "user", "content": "hi"}], context={})
        self.assertEqual(msgs[0]["role"], "user")
        self.assertIsNone(decision)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（run_before_model_call 不存在/flag 不生效）

**Step 3: impl**

在 `run_before_model_call`：
- 如果 hook 返回 `override_messages` 且 `enable_message_rewrite_hooks=False`：
  - 忽略 override
  - 仍记录 HookEvent（action="ignored_override_messages"）

**Step 4: pass**

---

## Task 5.3：HookMatcher 支持 `Edit|Write` OR 语法（skills 常用）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/hooks/engine.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_hook_matcher_or.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_hook_matcher_or.py`

```py
import unittest
from openagentic_sdk.hooks.engine import _match_name


class TestHookMatcherOr(unittest.TestCase):
    def test_or(self) -> None:
        self.assertTrue(_match_name("Edit|Write", "Edit"))
        self.assertTrue(_match_name("Edit|Write", "Write"))
        self.assertFalse(_match_name("Edit|Write", "Read"))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（_match_name 不存在）

**Step 3: impl**

新增 `_match_name(pattern: str, name: str) -> bool`：
- split `pattern` by `|`
- 对每段 `fnmatch.fnmatchcase(name, seg.strip())`

**Step 4: pass**

---

# Hour 6（5:00–6:00）Tools：Edit/Write/Bash/Web 的语义与安全边界（强测）

## Task 6.1：Write 原子写 + overwrite 语义测试

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/write.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_write_overwrite_and_atomic.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_write_overwrite_and_atomic.py`

```py
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.write import WriteTool


class TestWriteTool(unittest.TestCase):
    def test_overwrite_false_raises(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("x", encoding="utf-8")
            tool = WriteTool()
            with self.assertRaises(FileExistsError):
                tool.run_sync({"file_path": str(p), "content": "y", "overwrite": False}, ToolContext(cwd=str(root)))

    def test_atomic_write_does_not_leave_tmp(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            tool = WriteTool()
            tool.run_sync({"file_path": "a.txt", "content": "hi", "overwrite": True}, ToolContext(cwd=str(root)))
            # no tmp files left behind
            tmp_like = [x for x in root.iterdir() if x.name.endswith(".tmp")]
            self.assertEqual(tmp_like, [])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（当前 Write 可能不是原子写/不清理 tmp）

**Step 3: impl**

实现策略：
- 写入 `.<filename>.tmp`（同目录）
- fsync（可选）
- `Path.replace()` 原子替换
- finally 清理 tmp（如果 replace 前失败）

**Step 4: pass**

---

## Task 6.2：Edit 增强：count=0 replace all + replacements 精确

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/edit.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_edit_replacements_count0.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_edit_replacements_count0.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.edit import EditTool


class TestEditCountZero(unittest.TestCase):
    def test_count_zero_replaces_all(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("x x x", encoding="utf-8")
            tool = EditTool()
            out = tool.run_sync({"file_path": str(p), "old": "x", "new": "y", "count": 0}, ToolContext(cwd=str(root)))
            self.assertEqual(p.read_text(encoding="utf-8"), "y y y")
            self.assertEqual(out["replacements"], 3)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（当前 replacements 统计可能不准 / count=0 语义不明确）

**Step 3: impl**

- 约定：`count=0` 表示 replace all（与 Python 的 `str.replace(old, new)` 一致）
- `replacements` 必须是实际替换次数：
  - replace all：`text.count(old)`
  - replace N：`min(text.count(old), N)`

**Step 4: pass**

---

## Task 6.3：Edit 增强：上下文锚点（before/after）防误替换

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/edit.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_edit_with_context_anchors.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_edit_with_context_anchors.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.edit import EditTool


class TestEditAnchors(unittest.TestCase):
    def test_edit_requires_before_after_match(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("aaa\nTARGET\nbbb\n", encoding="utf-8")
            tool = EditTool()

            # Wrong anchors -> must fail
            with self.assertRaises(ValueError):
                tool.run_sync(
                    {"file_path": str(p), "old": "TARGET", "new": "OK", "before": "nope", "after": "bbb"},
                    ToolContext(cwd=str(root)),
                )

            # Correct anchors -> succeed
            out = tool.run_sync(
                {"file_path": str(p), "old": "TARGET", "new": "OK", "before": "aaa", "after": "bbb"},
                ToolContext(cwd=str(root)),
            )
            self.assertIn("replacements", out)
            self.assertEqual(p.read_text(encoding="utf-8"), "aaa\nOK\nbbb\n")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（EditTool 不支持 before/after）

**Step 3: impl（最小锚点算法）**

输入新增可选字段：
- `before: str | None`
- `after: str | None`

最小实现策略：

1) 读文件文本 `text`
2) 如果提供 `before`/`after`：
   - 先确认 `before` 与 `after` 都在文件里
   - 再确认出现顺序：`text.index(before) < text.index(old) < text.index(after)`
   - 若不满足则 raise ValueError
3) 然后再做 replace（count 默认 1）

**Step 4: pass**

---

## Task 6.4：Bash 输出截断标记（stdout_truncated/stderr_truncated）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/bash.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_bash_truncation_flags.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_bash_truncation_flags.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.bash import BashTool


class TestBashTruncation(unittest.TestCase):
    def test_stdout_truncation_flag(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            tool = BashTool(max_output_bytes=10, timeout_s=5.0)
            out = tool.run_sync({"command": "printf '12345678901234567890'"}, ToolContext(cwd=str(root)))
            self.assertTrue(out["stdout_truncated"])
            self.assertLessEqual(len(out["stdout"].encode("utf-8")), 10)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（当前 BashTool 不返回 truncation flags）

**Step 3: impl**

- 计算截断前后长度
- 输出字段补齐：
  - `stdout_truncated: bool`
  - `stderr_truncated: bool`

**Step 4: pass**

---

## Task 6.5：WebFetch SSRF 基本防护测试（localhost/private 默认拒绝）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/web_fetch.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_web_fetch_ssrf_block.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_web_fetch_ssrf_block.py`

```py
import unittest

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.web_fetch import WebFetchTool


class TestWebFetchSSRF(unittest.TestCase):
    def test_blocks_localhost_by_default(self) -> None:
        tool = WebFetchTool(allow_private_networks=False, transport=lambda *_: (200, {}, b"ok"))
        with self.assertRaises(ValueError):
            tool.run_sync({"url": "http://localhost/"}, ToolContext(cwd="/"))

    def test_allows_localhost_when_enabled(self) -> None:
        tool = WebFetchTool(allow_private_networks=True, transport=lambda *_: (200, {}, b"ok"))
        out = tool.run_sync({"url": "http://localhost/"}, ToolContext(cwd="/"))
        self.assertEqual(out["text"], "ok")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（如果工具当前没严格拦截 localhost/ip）

**Step 3: impl**

- 统一 hostname 判定：
  - `localhost` / `*.localhost` → blocked
  - IP（`ipaddress.ip_address`）且 `is_private/is_loopback/is_link_local` → blocked

**Step 4: pass**

---

## Task 6.6：WebSearch Tavily 输出结构稳定 + 缺 key 处理

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/web_search_tavily.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_web_search_output_shape.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_web_search_output_shape.py`

```py
import os
import unittest

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.web_search_tavily import WebSearchTool


class TestWebSearchShape(unittest.TestCase):
    def test_results_shape(self) -> None:
        os.environ["TAVILY_API_KEY"] = "test"

        def transport(url, headers, payload):
            return {"results": [{"title": "t", "url": "u", "snippet": "s"}]}

        tool = WebSearchTool(transport=transport)
        out = tool.run_sync({"query": "x", "max_results": 5}, ToolContext(cwd="/"))
        self.assertIn("results", out)
        r0 = out["results"][0]
        self.assertEqual(set(r0.keys()), {"title", "url", "content", "source"})
        self.assertEqual(r0["source"], "tavily")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（如果 keys 不一致）

**Step 3: impl**

- `content = r.get("content") or r.get("snippet") or ""`
- 保证 title/url/content 都是 str（缺失时用 `""`）

**Step 4: pass**

---

# Hour 7（6:00–7:00）Providers：OpenAI Streaming（SSE）+ OpenAI-compatible

## Task 7.1：为 OpenAIProvider 增加 `stream(...)`（离线可测）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/providers/openai.py`
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/providers/sse.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_openai_sse_parser.py`

**Step 1: failing test（SSE parser）**

`packages/sdk/openagentic-sdk/tests/test_openai_sse_parser.py`

```py
import unittest

from openagentic_sdk.providers.sse import parse_sse_events


class TestSSEParser(unittest.TestCase):
    def test_parses_data_lines(self) -> None:
        raw = b"data: {\\\"x\\\":1}\\n\\n" + b"data: [DONE]\\n\\n"
        events = list(parse_sse_events(raw.splitlines(keepends=True)))
        self.assertEqual(events[0], '{"x":1}')
        self.assertEqual(events[1], "[DONE]")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（无 sse.py）

**Step 3: minimal impl**

实现 `parse_sse_events(lines_iter)`：
- 只识别 `data:` 行
- 以空行分隔事件
- 每个事件把 data 行拼成一个字符串（多行 data 拼接）

**Step 4: pass**

---

## Task 7.2：OpenAI tool-call streaming 组装器（arguments 分段拼接）

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/providers/openai_stream_assembler.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_openai_tool_call_assembler.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_openai_tool_call_assembler.py`

```py
import unittest

from openagentic_sdk.providers.openai_stream_assembler import ToolCallAssembler


class TestToolCallAssembler(unittest.TestCase):
    def test_assembles_arguments(self) -> None:
        a = ToolCallAssembler()
        a.apply_delta({"id": "call_1", "function": {"name": "Read", "arguments": "{\\\"file_"} })
        a.apply_delta({"id": "call_1", "function": {"arguments": "path\\\":\\\"a.txt\\\"}"} })
        calls = a.finalize()
        self.assertEqual(calls[0].name, "Read")
        self.assertEqual(calls[0].arguments["file_path"], "a.txt")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（assembler 不存在）

**Step 3: impl**

`ToolCallAssembler`：
- map: id → {name, arguments_str}
- `apply_delta(delta)`：
  - name 只在首次出现时设置
  - arguments_str 追加
- `finalize()`：
  - 对每个 id：
    - `json.loads(arguments_str)` → dict
    - 产出 `ToolCall(tool_use_id=id, name=name, arguments=dict)`

**Step 4: pass**

---

## Task 7.3：OpenAIProvider.stream（通过注入 transport 模拟）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/providers/openai.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_openai_provider_stream.py`

**Step 1: failing test（不走网络）**

测试策略：
- 注入一个 `stream_transport(payload)-> iterable[bytes]`，返回 SSE bytes chunks
- provider.stream 解析并产出：
  - text deltas（list[str]）
  - assembled tool calls（list[ToolCall]）

`packages/sdk/openagentic-sdk/tests/test_openai_provider_stream.py`

```py
import unittest

from openagentic_sdk.providers.openai import OpenAIProvider


def _sse(*payloads: str) -> list[bytes]:
    # Helper: build minimal SSE byte chunks
    out: list[bytes] = []
    for p in payloads:
        out.append(f"data: {p}\n\n".encode("utf-8"))
    return out


class TestOpenAIProviderStream(unittest.IsolatedAsyncioTestCase):
    async def test_stream_yields_text_and_tool_calls(self) -> None:
        chunks = _sse(
            '{"choices":[{"delta":{"content":"he"}}]}',
            '{"choices":[{"delta":{"content":"llo"}}]}',
            '{"choices":[{"delta":{"tool_calls":[{"id":"call_1","function":{"name":"Read","arguments":"{\\"file_"}}]}}]}',
            '{"choices":[{"delta":{"tool_calls":[{"id":"call_1","function":{"arguments":"path\\":\\"a.txt\\"}"}}]}}]}',
            "[DONE]",
        )

        def stream_transport(url, headers, payload):
            # No network: just return our prepared chunks
            return iter(chunks)

        provider = OpenAIProvider(stream_transport=stream_transport)
        events = []
        async for ev in provider.stream(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": "read a.txt"}],
            tools=[],
            api_key="sk-test",
        ):
            events.append(ev)

        text = "".join(e.delta for e in events if e.type == "text_delta")
        self.assertEqual(text, "hello")

        tool_calls = [e.tool_call for e in events if e.type == "tool_call"]
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].name, "Read")
        self.assertEqual(tool_calls[0].arguments["file_path"], "a.txt")


if __name__ == "__main__":
    unittest.main()
```

Run: `PYTHONPATH=packages/sdk/openagentic-sdk python3 -m unittest -q packages/sdk/openagentic-sdk/tests/test_openai_provider_stream.py`
Expected: FAIL（当前 OpenAIProvider 无 stream/stream_transport）

**Step 2: impl**

在 `OpenAIProvider` 增加：
- `stream(...) -> AsyncIterator[ProviderStreamEvent]`（新类型）
- 或最小：`stream_complete(...) -> ModelOutput`（内部拼 SSE，但不 yield delta；这样会损失 `assistant.delta`）

v0.1 推荐：真正 yield delta（因为你前面要求能力强）。

**Step 3: pass**

---

## Task 7.4：OpenAI-compatible 第二 Provider（同协议，base_url 可配置）

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/providers/openai_compatible.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_openai_compatible_provider.py`

**Step 1: failing test（header/base_url）**

`packages/sdk/openagentic-sdk/tests/test_openai_compatible_provider.py`

```py
import unittest

from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider
from openagentic_sdk.providers.base import ModelOutput


class TestOpenAICompatibleProvider(unittest.IsolatedAsyncioTestCase):
    async def test_uses_base_url_and_headers(self) -> None:
        seen = {}

        def transport(url, headers, payload):
            seen["url"] = url
            seen["headers"] = dict(headers)
            return {"choices": [{"message": {"content": "ok"}}]}

        p = OpenAICompatibleProvider(
            base_url="https://example.test/v1",
            transport=transport,
            api_key_header="x-api-key",
        )

        out = await p.complete(model="m", messages=[{"role": "user", "content": "hi"}], api_key="k")
        self.assertIsInstance(out, ModelOutput)
        self.assertTrue(seen["url"].startswith("https://example.test/v1"))
        self.assertEqual(seen["headers"]["x-api-key"], "k")


if __name__ == "__main__":
    unittest.main()
```

---

# Hour 8（7:00–8:00）Runtime：接入 streaming + tool schema + tool error policy

## Task 8.1：runtime 支持 provider.stream → assistant.delta

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_runtime_streaming.py`

**Step 1: failing test（FakeStreamingProvider）**

`packages/sdk/openagentic-sdk/tests/test_runtime_streaming.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.sessions.store import FileSessionStore


class FakeStreamingProvider:
    name = "fake-stream"

    async def stream(self, *, model, messages, tools=(), api_key=None):
        yield {"type": "text_delta", "delta": "he"}
        yield {"type": "text_delta", "delta": "llo"}
        yield {"type": "done"}


class TestRuntimeStreaming(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_emits_assistant_delta(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgenticOptions(
                provider=FakeStreamingProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
            )
            import openagentic_sdk

            types = []
            async for e in openagentic_sdk.query(prompt="hi", options=options):
                types.append(getattr(e, "type", None))
            self.assertIn("assistant.delta", types)
            self.assertIn("assistant.message", types)
            self.assertIn("result", types)


if __name__ == "__main__":
    unittest.main()
```

---

# Hour 9（8:00–9:00）Skills（实现重点）：索引/解析/工具/激活/注入

> 这一小时只做“skills 的核心基建”，不做 MCP、不做自动执行 DSL，但要让 skills 在 agent loop 里“真的能用起来”（模型能发现、能加载、能激活、能按照 skill 指令调用工具）。

## Task 9.1：实现 `skills` 模块（index + parser）

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/skills/__init__.py`
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/skills/index.py`
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/skills/parse.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_skill_parser.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_skill_index.py`

**Step 1: failing test（parser，完整代码）**

`packages/sdk/openagentic-sdk/tests/test_skill_parser.py`

```py
import unittest

from openagentic_sdk.skills.parse import parse_skill_markdown


SKILL_MD = \"\"\"# skill-example

One line summary.

## Checklist
- Do A
- Do B

## Notes
Use the Read tool first.
\"\"\"


class TestSkillParser(unittest.TestCase):
    def test_parses_name_summary_checklist(self) -> None:
        s = parse_skill_markdown(SKILL_MD)
        self.assertEqual(s.name, "skill-example")
        self.assertEqual(s.summary, "One line summary.")
        self.assertEqual(s.checklist, ["Do A", "Do B"])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（skills 模块不存在）

**Step 3: minimal impl（parser 策略）**

`parse_skill_markdown(text: str) -> SkillDoc`：

- `name`：第一行 `# ` 后的标题（trim）
- `summary`：标题后第一段非空文本（直到空行）
- `checklist`：找到 “Checklist” 标题后面的 `- ` 列表项（收集到下一个标题为止）
- 其他：保留 `raw`（原始 markdown），未来扩展

**Step 4: pass**

---

**Step 5: failing test（index，完整代码）**

`packages/sdk/openagentic-sdk/tests/test_skill_index.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.skills.index import index_skills


class TestSkillIndex(unittest.TestCase):
    def test_indexes_claude_skills(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".claude" / "skills" / "a"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text("# a\\n\\nsummary\\n", encoding="utf-8")

            skills = index_skills(project_dir=str(root))
            self.assertEqual(len(skills), 1)
            self.assertEqual(skills[0].name, "a")
            self.assertTrue(skills[0].path.endswith("SKILL.md"))


if __name__ == "__main__":
    unittest.main()
```

**Step 6: run & fail**

Expected: FAIL（index_skills 不存在）

**Step 7: minimal impl（index 策略）**

`index_skills(project_dir)`：
- 扫描 `.claude/skills/**/SKILL.md`
- 对每个文件：
  - 读取内容 → parse_skill_markdown
  - name 优先用标题，否则 fallback 目录名
  - 产出 `SkillInfo(name, summary, path)`
- 输出按 name 排序

**Step 8: pass**

---

## Task 9.2：Skill 工具：SkillList / SkillLoad / SkillActivate

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/skill_list.py`
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/skill_load.py`
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/skill_activate.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/defaults.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_skill_tools.py`

**Step 1: failing test（SkillLoad 输出结构稳定）**

`packages/sdk/openagentic-sdk/tests/test_skill_tools.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.skill_load import SkillLoadTool


class TestSkillTools(unittest.TestCase):
    def test_skill_load(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".claude" / "skills" / "ex"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text("# ex\\n\\nsummary\\n\\n## Checklist\\n- A\\n", encoding="utf-8")
            tool = SkillLoadTool()
            out = tool.run_sync({"name": "ex", "project_dir": str(root)}, ToolContext(cwd=str(root)))
            self.assertEqual(out["name"], "ex")
            self.assertEqual(out["summary"], "summary")
            self.assertEqual(out["checklist"], ["A"])
            self.assertIn("content", out)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（SkillLoadTool 不存在）

**Step 3: impl**

- `SkillListTool`：
  - input：`project_dir?`
  - output：`skills: [{name,summary,path}]`
- `SkillLoadTool`：
  - input：`name`, `project_dir?`
  - output：`{name,summary,checklist,content,path}`
- `SkillActivateTool`：
  - input：`name`
  - output：`{active: [..]}`（返回激活后的列表）

激活的状态不能只存在内存（要可审计+可 resume）：
- 增加事件：`skill.activated`（包含 name）
- runtime 在每次 model call 前，从 session events 重建 active skills（最小）或维护内存并同时落事件

**Step 4: pass**

---

## Task 9.3：runtime 注入 skills index + active skills（system prompt）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/project/claude.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_runtime_skill_injection.py`

**Step 1: failing test（捕获 messages）**

`packages/sdk/openagentic-sdk/tests/test_runtime_skill_injection.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.sessions.store import FileSessionStore


class RecordingProvider:
    name = "recording"

    def __init__(self) -> None:
        self.seen = []

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self.seen.append(list(messages))
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestRuntimeSkillInjection(unittest.IsolatedAsyncioTestCase):
    async def test_injects_memory_and_skill_index(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "CLAUDE.md").write_text("project memory", encoding="utf-8")
            skill_dir = root / ".claude" / "skills" / "example"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# example\n\nSummary line.\n", encoding="utf-8")
            cmd_dir = root / ".claude" / "commands"
            cmd_dir.mkdir(parents=True)
            (cmd_dir / "hello.md").write_text("hello", encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            provider = RecordingProvider()
            options = OpenAgenticOptions(
                provider=provider,
                model="m",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                setting_sources=["project"],
                project_dir=str(root),
            )

            import openagentic_sdk

            async for _ in openagentic_sdk.query(prompt="hi", options=options):
                pass

            first_call_msgs = provider.seen[0]
            self.assertEqual(first_call_msgs[0]["role"], "system")
            sys = first_call_msgs[0]["content"]
            self.assertIn("project memory", sys)
            self.assertIn("example", sys)  # skill name appears in index
            self.assertIn("SKILL.md", sys)  # path appears in index


if __name__ == "__main__":
    unittest.main()
```

Run: `PYTHONPATH=packages/sdk/openagentic-sdk python3 -m unittest -q packages/sdk/openagentic-sdk/tests/test_runtime_skill_injection.py`
Expected: FAIL（目前 runtime 未注入 `.claude` skills/memory 到 system message）

---

# Hour 10（9:00–10:00）Skills 测试套件（重点）：fixtures + e2e + 回归

## Task 10.1：新增 skills fixtures（3 套项目）

**Files:**
- Create: `packages/sdk/openagentic-sdk/tests/fixtures/claude_project_min/CLAUDE.md`
- Create: `packages/sdk/openagentic-sdk/tests/fixtures/claude_project_min/.claude/skills/example/SKILL.md`
- Create: `packages/sdk/openagentic-sdk/tests/fixtures/claude_project_min/.claude/commands/hello.md`
- Create: `packages/sdk/openagentic-sdk/tests/fixtures/claude_project_checklist/.claude/skills/check/SKILL.md`
- Create: `packages/sdk/openagentic-sdk/tests/fixtures/claude_project_nested/.claude/skills/a/SKILL.md`
- Create: `packages/sdk/openagentic-sdk/tests/fixtures/claude_project_nested/.claude/skills/b/SKILL.md`

**Step 1: fixture 内容规范（建议模板）**

`SKILL.md` 最小模板（用于测试）：

```md
# skill-name

Summary line.

## Checklist
- Step 1
- Step 2

## Tooling
Use Read, Grep, Edit.
```

---

## Task 10.2：skills 端到端：FakeProvider 根据 skill checklist 触发工具调用

**Files:**
- Create: `packages/sdk/openagentic-sdk/tests/test_skill_e2e_tooling.py`

**Step 1: failing test（e2e）**

目标：验证“skills 能真的跑起来”：
- runtime 注入 skill index
- provider（假的）选择调用 `SkillLoad`（加载 checklist）
- provider 再调用 `Grep` / `Read`（模拟按 skill 指示）
- runtime 执行工具并回灌 tool results
- 最终产出 Result

测试中用一个 “脚本化 provider”：
- 第 1 次 complete：tool_call SkillLoad(name="check")
- 第 2 次 complete：tool_call Grep(query="TODO", ...)
- 第 3 次 complete：assistant_text="done"

断言：
- events 中出现 `tool.use`(SkillLoad)→`tool.result`
- 出现 `tool.use`(Grep)→`tool.result`
- 出现 `result`

`packages/sdk/openagentic-sdk/tests/test_skill_e2e_tooling.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class ScriptedProvider:
    name = "scripted"

    def __init__(self) -> None:
        self.step = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        # 0: load skill
        if self.step == 0:
            self.step += 1
            return ModelOutput(assistant_text=None, tool_calls=[ToolCall("s1", "SkillLoad", {"name": "check"})])
        # 1: grep
        if self.step == 1:
            self.step += 1
            return ModelOutput(assistant_text=None, tool_calls=[ToolCall("g1", "Grep", {"query": "TODO", "file_glob": "**/*.txt"})])
        # 2: done
        return ModelOutput(assistant_text="done", tool_calls=[])


class TestSkillE2E(unittest.IsolatedAsyncioTestCase):
    async def test_skill_flow_runs_tools(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "t.txt").write_text("TODO: x\n", encoding="utf-8")
            p = root / ".claude" / "skills" / "check"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text("# check\n\nFind TODOs.\n\n## Checklist\n- Use Grep\n", encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            options = OpenAgenticOptions(
                provider=ScriptedProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                setting_sources=["project"],
                project_dir=str(root),
            )

            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="run check", options=options):
                events.append(e)

            types = [getattr(e, "type", None) for e in events]
            self.assertIn("tool.use", types)
            self.assertIn("tool.result", types)
            self.assertIn("result", types)

            # Ensure both tool calls happened
            used = [getattr(e, "name", None) for e in events if getattr(e, "type", None) == "tool.use"]
            self.assertIn("SkillLoad", used)
            self.assertIn("Grep", used)


if __name__ == "__main__":
    unittest.main()
```

---

## Task 10.3：skills 回归测试矩阵（至少 12 个 case）

**Files:**
- Create: `packages/sdk/openagentic-sdk/tests/test_skill_matrix.py`

覆盖点建议（每个 case 一个 test_* 方法）：

1) 无 `.claude/skills` → SkillList 返回空
2) skill 缺少标题 → name fallback 到目录名
3) checklist 缺失 → checklist=[]
4) checklist 含空行/缩进 → parser 仍稳定
5) SkillLoad name 不存在 → FileNotFoundError/ValueError（明确错误类型）
6) runtime 注入 skill index：包含 path（可点开）
7) active skill 事件落盘后，resume 后仍 active
8) skills index 排序稳定（按 name）
9) skill summary 提取：只取第一段
10) nested skills 多个：索引全部
11) SkillActivate 重复激活：去重保持顺序
12) hooks 能在 PreToolUse 拦截 SkillLoad 并改写 project_dir（测试 rewrite）

`packages/sdk/openagentic-sdk/tests/test_skill_matrix.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.skills.index import index_skills
from openagentic_sdk.skills.parse import parse_skill_markdown


class TestSkillMatrix(unittest.TestCase):
    def test_no_skills_dir_returns_empty(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            skills = index_skills(project_dir=str(root))
            self.assertEqual(skills, [])

    def test_missing_title_falls_back_to_dir_name(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / ".claude" / "skills" / "x"
            p.mkdir(parents=True)
            (p / "SKILL.md").write_text("no title here\n\nsummary\n", encoding="utf-8")
            skills = index_skills(project_dir=str(root))
            self.assertEqual(skills[0].name, "x")

    def test_checklist_missing_is_empty(self) -> None:
        s = parse_skill_markdown("# a\n\nsummary\n\n## Notes\nx\n")
        self.assertEqual(s.checklist, [])

    def test_checklist_ignores_blank_items(self) -> None:
        s = parse_skill_markdown("# a\n\nsummary\n\n## Checklist\n- A\n-\n-  \n- B\n")
        self.assertEqual(s.checklist, ["A", "B"])

    def test_summary_first_paragraph_only(self) -> None:
        s = parse_skill_markdown("# a\n\nfirst.\n\nsecond.\n")
        self.assertEqual(s.summary, "first.")

    def test_index_sorted_by_name(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            for name in ["b", "a"]:
                p = root / ".claude" / "skills" / name
                p.mkdir(parents=True)
                (p / "SKILL.md").write_text(f"# {name}\n\nsummary\n", encoding="utf-8")
            skills = index_skills(project_dir=str(root))
            self.assertEqual([s.name for s in skills], ["a", "b"])

    # Remaining cases (runtime injection, SkillActivate persistence, hook rewrite)
    # are covered by dedicated runtime/tool tests to avoid duplicating runtime scaffolding here.


if __name__ == "__main__":
    unittest.main()
```

Run: `PYTHONPATH=packages/sdk/openagentic-sdk python3 -m unittest -q packages/sdk/openagentic-sdk/tests/test_skill_matrix.py`
Expected: FAIL until `openagentic_sdk.skills.*` is implemented and stable.

---

## Task 10.4：文档与 examples：让用户知道如何写技能与如何让 agent 用它

**Files:**
- Modify: `packages/sdk/openagentic-sdk/README.md`
- Create: `packages/sdk/openagentic-sdk/examples/skills_index.py`
- Create: `packages/sdk/openagentic-sdk/examples/skills_activate.py`
- Create: `packages/sdk/openagentic-sdk/examples/skills_e2e_fake_provider.py`

文档必须包含：
- `.claude/skills/**/SKILL.md` 结构约定
- “强烈建议”：不要把整个 skill 内容塞进系统 prompt；用 SkillLoad/Read 动态加载
- “安全提示”：Bash/Web 默认危险，配合 permission gate


---

## Task 3.3：SessionStore 记录 meta：provider/model/options 摘要

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/store.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_session_meta.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_session_meta.py`

```py
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.sessions.store import FileSessionStore


class NoopProvider:
    name = "noop"

    async def complete(self, *, model, messages, tools=(), api_key=None):
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestSessionMeta(unittest.IsolatedAsyncioTestCase):
    async def test_meta_written(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgenticOptions(
                provider=NoopProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
            )
            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="hi", options=options):
                events.append(e)
            sid = next(e.session_id for e in events if getattr(e, "type", None) == "system.init")
            meta = json.loads((root / "sessions" / sid / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["metadata"]["cwd"], str(root))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（目前 meta 只写 cwd，没统一策略或字段不同）

**Step 3: impl**

设计 v0.1 meta 最小字段：

- `session_id`
- `created_at`
- `metadata`（包含）：
  - `cwd`
  - `provider_name`
  - `model`
  - `setting_sources`（如有）
  - `allowed_tools`（如有，注意隐私）

在 runtime 创建 session 时传入 metadata；store 按 indent=2 JSON 写入。

**Step 4: pass**

---

## Task 3.4：SessionStore 支持“父子关系”落盘（subagent）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/store.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_session_parent_child_link.py`

**Step 1: failing test**

`packages/sdk/openagentic-sdk/tests/test_session_parent_child_link.py`

```py
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import AgentDefinition, OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class TaskProvider:
    name = "fake"

    def __init__(self):
        self.calls = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self.calls += 1
        if self.calls == 1:
            return ModelOutput(assistant_text=None, tool_calls=[ToolCall("t1", "Task", {"agent": "worker", "prompt": "x"})])
        # after Task
        if any(m.get("role") == "tool" for m in messages):
            return ModelOutput(assistant_text="done", tool_calls=[])
        # child
        return ModelOutput(assistant_text="child", tool_calls=[])


class TestSessionLink(unittest.IsolatedAsyncioTestCase):
    async def test_child_meta_contains_parent(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgenticOptions(
                provider=TaskProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
                agents={"worker": AgentDefinition(description="d", prompt="child", tools=())},
            )
            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="parent", options=options):
                events.append(e)
            # tool.result for Task contains child_session_id
            tr = next(e for e in events if getattr(e, "type", None) == "tool.result" and getattr(e, "tool_use_id", None) == "t1")
            child_sid = tr.output["child_session_id"]
            meta = json.loads((root / "sessions" / child_sid / "meta.json").read_text(encoding="utf-8"))
            self.assertIn("parent_session_id", meta["metadata"])
            self.assertIn("parent_tool_use_id", meta["metadata"])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（child meta 未记录 parent）

**Step 3: impl**

在 runtime 创建 child session 时，metadata 必须包含：
- `parent_session_id`
- `parent_tool_use_id`
- `agent_name`

**Step 4: pass**

---

# Hour 4（3:00–4:00）Permissions：可测试交互审批 + AskUserQuestion 事件

## Task 4.1：抽离 interactive 模块（注入 input_fn，unittest 可控）

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/permissions/interactive.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/permissions/gate.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_permissions_prompt.py`

**Step 1: failing test（完整代码）**

`packages/sdk/openagentic-sdk/tests/test_permissions_prompt.py`

```py
import unittest

from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.permissions.interactive import InteractiveApprover


class TestPermissionsPrompt(unittest.IsolatedAsyncioTestCase):
    async def test_prompt_denies_on_no(self) -> None:
        approver = InteractiveApprover(input_fn=lambda _: "no")
        gate = PermissionGate(permission_mode="prompt", interactive=True, interactive_approver=approver)
        ok = await gate.approve("Bash", {"command": "echo hi"}, context={})
        self.assertFalse(ok)

    async def test_prompt_allows_on_yes(self) -> None:
        approver = InteractiveApprover(input_fn=lambda _: "yes")
        gate = PermissionGate(permission_mode="prompt", interactive=True, interactive_approver=approver)
        ok = await gate.approve("Bash", {"command": "echo hi"}, context={})
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（gate 没有 interactive_approver 注入点）

**Step 3: impl**

1) `interactive.py`：

```py
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class InteractiveApprover:
    input_fn: callable

    def ask_yes_no(self, prompt: str) -> bool:
        ans = str(self.input_fn(prompt)).strip().lower()
        return ans in ("y", "yes")
```

2) `gate.py` 增加字段：
- `interactive_approver: InteractiveApprover | None = None`

prompt 模式：
- 如果 `interactive` 为真但 `interactive_approver` 为空：raise ValueError（更可控）
- 否则调用 `interactive_approver.ask_yes_no(...)`

**Step 4: pass**

---

## Task 4.2：AskUserQuestion 事件模型（非交互 host）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/events.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_ask_user_question.py`

**Step 1: failing test**

场景：`permission_mode="prompt"` 但 `interactive=False` 且 host 提供 `user_answerer` 回调。

`packages/sdk/openagentic-sdk/tests/test_ask_user_question.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class ProviderAsksTool:
    name = "fake"
    async def complete(self, *, model, messages, tools=(), api_key=None):
        return ModelOutput(assistant_text=None, tool_calls=[ToolCall("tc1", "Bash", {"command": "echo hi"})])


class TestAskUserQuestion(unittest.IsolatedAsyncioTestCase):
    async def test_emits_question_and_uses_answerer(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)

            async def answerer(q):
                return "yes"

            options = OpenAgenticOptions(
                provider=ProviderAsksTool(),
                model="m",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="prompt", interactive=False, user_answerer=answerer),
            )
            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="go", options=options):
                events.append(e)
                if getattr(e, "type", None) == "tool.result":
                    break
            self.assertTrue(any(getattr(e, "type", None) == "user.question" for e in events))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Expected: FAIL（目前没有 user.question 事件，也没有 user_answerer）

**Step 3: impl**

- 新增事件 `UserQuestion`：
  - `type="user.question"`
  - `question_id`
  - `prompt`
  - `choices`（例如 `["yes","no"]`）
- 在 PermissionGate 增加字段 `user_answerer`（async callback）：
  - prompt 模式且 interactive=False：
    1) 生成 question event（由 runtime emit）
    2) 调用 answerer 获取 choice
    3) 返回 allow/deny

注意：为避免 gate 直接 yield 事件，建议：
- `PermissionGate.approve(...)` 返回一个结构：
  - `ApprovalResult(allowed: bool, question_event: UserQuestion|None)`
- runtime 负责 emit question_event 并落盘

**Step 4: pass**


---

# Hour 3（2:00–3:00）Sessions：真正 resume（重建 messages）+ 截断策略

## Task 3.1：实现 `SessionRebuilder`（events → messages）

**Files:**
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/rebuild.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/store.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_resume_rebuild_messages.py`

**Step 1: failing test（完整代码）**

`packages/sdk/openagentic-sdk/tests/test_resume_rebuild_messages.py`

```py
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.sessions.store import FileSessionStore


class FakeProvider:
    name = "fake"

    def __init__(self) -> None:
        self.seen_messages = []
        self.calls = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self.seen_messages.append(list(messages))
        self.calls += 1
        # First call: request tool
        if self.calls == 1:
            return ModelOutput(assistant_text=None, tool_calls=[ToolCall("tc1", "Read", {"file_path": "a.txt"})])
        # Second call: finish
        return ModelOutput(assistant_text="done", tool_calls=[])


class TestResumeRebuild(unittest.IsolatedAsyncioTestCase):
    async def test_resume_rebuilds_messages(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            store = FileSessionStore(root_dir=root)

            provider1 = FakeProvider()
            options1 = OpenAgenticOptions(
                provider=provider1,
                model="fake",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
            )

            import openagentic_sdk

            events1 = []
            async for e in openagentic_sdk.query(prompt="read it", options=options1):
                events1.append(e)
            sid = next(e.session_id for e in events1 if getattr(e, "type", None) == "system.init")

            provider2 = FakeProvider()
            options2 = OpenAgenticOptions(
                provider=provider2,
                model="fake",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
                resume=sid,
            )

            async for _ in openagentic_sdk.query(prompt="continue", options=options2):
                pass

            # provider2 first call should include rebuilt history (at least 1 tool message)
            first = provider2.seen_messages[0]
            roles = [m.get("role") for m in first]
            self.assertIn("tool", roles)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: run & fail**

Run: `PYTHONPATH=packages/sdk/openagentic-sdk python3 -m unittest -q packages/sdk/openagentic-sdk/tests/test_resume_rebuild_messages.py`
Expected: FAIL（当前 resume 不重建 messages）

**Step 3: minimal impl**

1) 新增 `sessions/rebuild.py`：
   - `def rebuild_messages(events: list[Event]) -> list[dict]`
2) 重建规则（v0.1 最小）：
   - `UserMessage` → `{"role":"user","content":text}`
   - `AssistantMessage` → `{"role":"assistant","content":text}`
   - `ToolUse`（可选）→（通常不需要直接重建）
   - `ToolResult` → `{"role":"tool","tool_call_id": tool_use_id, "content": json.dumps(output)}`
3) `runtime.query()`：
   - 如果 `resume` 存在：读取 `store.read_events(resume)` → rebuild → 初始化 messages = rebuilt + 新 user prompt

**Step 4: run & pass**

---

## Task 3.2：resume 截断（按 event 数量与字节数）

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/options.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/rebuild.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_resume_limits.py`

**Step 1: failing test**

构造 2000 条事件（可重复写入 `AssistantMessage`），设置 `resume_max_events=200`，验证 rebuild 后不超过 200 条 messages。

`packages/sdk/openagentic-sdk/tests/test_resume_limits.py`

```py
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.events import AssistantMessage, SystemInit
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.sessions.rebuild import rebuild_messages


class TestResumeLimits(unittest.TestCase):
    def test_rebuild_applies_max_events(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session()
            store.append_event(sid, SystemInit(session_id=sid, cwd="/x", sdk_version="0.0.0"))
            for i in range(2000):
                store.append_event(sid, AssistantMessage(text=f"m{i}"))

            events = store.read_events(sid)
            msgs = rebuild_messages(events, max_events=200, max_bytes=10_000_000)
            self.assertLessEqual(len(msgs), 200)

    def test_rebuild_applies_max_bytes(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session()
            store.append_event(sid, SystemInit(session_id=sid, cwd="/x", sdk_version="0.0.0"))
            # Create large messages
            for i in range(200):
                store.append_event(sid, AssistantMessage(text="x" * 1000))

            events = store.read_events(sid)
            msgs = rebuild_messages(events, max_events=1000, max_bytes=10_000)  # tiny cap
            # It's acceptable if we end up with 0..N messages; we just must not exceed max_bytes.
            total = sum(len((m.get("content") or "").encode("utf-8")) for m in msgs)
            self.assertLessEqual(total, 10_000)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: impl**

- `OpenAgenticOptions` 增加：
  - `resume_max_events: int = 1000`
  - `resume_max_bytes: int = 2_000_000`
- `rebuild_messages` 先截断 events 再 rebuild

**Step 3: pass**
