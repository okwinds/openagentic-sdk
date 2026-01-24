import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk import query
from openagentic_sdk.options import CompactionOptions, OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.tools.read import ReadTool
from openagentic_sdk.tools.registry import ToolRegistry


class OverflowThenContinueProvider:
    name = "fake-legacy"

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self._n = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self._n += 1
        self.calls.append({"model": model, "messages": list(messages), "tools": list(tools)})

        # 1) Normal assistant step (but with usage that exceeds the configured budget)
        if self._n == 1:
            return ModelOutput(
                assistant_text="hi",
                tool_calls=(),
                usage={"input_tokens": 8000, "output_tokens": 10, "total_tokens": 8010},
                raw=None,
                response_id=None,
            )

        # 2) Compaction pass (tool-less) - return a summary pivot.
        if self._n == 2:
            sys0 = messages[0] if messages else {}
            assert isinstance(sys0, dict) and sys0.get("role") == "system"
            assert "summarizing" in (sys0.get("content") or "")
            return ModelOutput(
                assistant_text="SUMMARY: did X, next do Y",
                tool_calls=(),
                usage={"total_tokens": 1},
                raw=None,
                response_id=None,
            )

        # 3) Auto-continue after compaction.
        return ModelOutput(
            assistant_text="done",
            tool_calls=(),
            usage={"total_tokens": 2},
            raw=None,
            response_id=None,
        )


class ToolOutputPruneProvider:
    name = "fake-legacy"

    def __init__(self) -> None:
        self._n = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self._n += 1

        # First call: request multiple reads that will produce large tool outputs.
        if self._n == 1:
            calls = [
                ToolCall(tool_use_id=f"call_{i}", name="Read", arguments={"file_path": "big.txt"})
                for i in range(3)
            ]
            return ModelOutput(assistant_text=None, tool_calls=calls, usage={"total_tokens": 1}, raw=None, response_id=None)

        # Second call: ensure tool outputs were compacted in the rebuilt history.
        tool_msgs = [m for m in messages if isinstance(m, dict) and m.get("role") == "tool"]
        self.assertTrue(len(tool_msgs) >= 1)
        # At least one tool output should be replaced with the placeholder.
        self.assertTrue(any((m.get("content") or "") == "[Old tool result content cleared]" for m in tool_msgs))

        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 2}, raw=None, response_id=None)

    # unittest-style assertion helpers (avoid importing unittest in provider call sites)
    def assertTrue(self, cond: bool) -> None:
        if not cond:
            raise AssertionError("assertTrue failed")


class TestCompactionAutoAndPrune(unittest.IsolatedAsyncioTestCase):
    async def test_auto_compaction_inserts_marker_and_summary_and_continues(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)

            provider = OverflowThenContinueProvider()
            options = OpenAgenticOptions(
                provider=provider,
                model="fake",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                # Configure a context window that makes the first step overflow.
                compaction=CompactionOptions(auto=True, prune=False, context_limit=9000, global_output_cap=4096),
            )

            events = []
            async for e in query(prompt="hello", options=options):
                events.append(e)

            # 3 provider calls: normal step, compaction summarizer, post-compaction continue.
            self.assertEqual(len(provider.calls), 3)

            # The event stream includes a compaction marker and a summary pivot.
            self.assertTrue(any(getattr(e, "type", "") == "user.compaction" for e in events))
            self.assertTrue(
                any(getattr(e, "type", "") == "assistant.message" and bool(getattr(e, "is_summary", False)) for e in events)
            )

            # Final output should be the post-compaction assistant message.
            final = next(e for e in reversed(events) if getattr(e, "type", "") == "result")
            self.assertEqual(getattr(final, "final_text", ""), "done")

    async def test_tool_output_pruning_replaces_old_outputs_in_model_input(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            # Create a large file so Read tool outputs are big.
            (root / "big.txt").write_text("x" * 50_000, encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            tools = ToolRegistry([ReadTool()])
            provider = ToolOutputPruneProvider()

            options = OpenAgenticOptions(
                provider=provider,
                model="fake",
                api_key="x",
                cwd=str(root),
                session_store=store,
                tools=tools,
                permission_gate=PermissionGate(permission_mode="bypass"),
                compaction=CompactionOptions(
                    auto=False,
                    prune=True,
                    context_limit=0,
                    protect_tool_output_tokens=1,
                    min_prune_tokens=1,
                ),
            )

            # Run once; provider asserts the second call receives placeholder tool outputs.
            out = []
            async for e in query(prompt="read", options=options):
                out.append(e)

            self.assertTrue(any(getattr(e, "type", "") == "tool.output_compacted" for e in out))
            self.assertTrue(any(getattr(e, "type", "") == "result" for e in out))


if __name__ == "__main__":
    unittest.main()
