import asyncio
import unittest


class _FakePlugin:
    def __init__(self) -> None:
        self.id = "fake"
        self.meta = type("Meta", (), {"aliases": []})
        self.started: list[str] = []
        self.stopped: list[str] = []
        self._abort: dict[str, asyncio.Event] = {}

    def list_account_ids(self) -> list[str]:
        return ["a1", "a2"]

    async def start_account(self, *, account_id: str, abort: asyncio.Event) -> None:
        self.started.append(account_id)
        self._abort[account_id] = abort
        await abort.wait()

    async def stop_account(self, *, account_id: str) -> None:
        self.stopped.append(account_id)


class TestChannelManager(unittest.TestCase):
    def test_start_stop_tracks_status(self) -> None:
        async def _run() -> None:
            from openagentic_gateway.channels.manager import ChannelManager
            from openagentic_gateway.channels.registry import ChannelRegistry

            plugin = _FakePlugin()
            reg = ChannelRegistry()
            reg.register(plugin)
            mgr = ChannelManager(registry=reg)

            await mgr.start_channel("fake")
            await asyncio.sleep(0)
            snap = mgr.get_runtime_snapshot()
            self.assertTrue(snap["channels"]["fake"].running)
            self.assertEqual(set(plugin.started), {"a1", "a2"})

            await mgr.stop_channel("fake")
            snap2 = mgr.get_runtime_snapshot()
            self.assertFalse(snap2["channels"]["fake"].running)
            self.assertEqual(set(plugin.stopped), {"a1", "a2"})

        asyncio.run(_run())

    def test_start_is_idempotent_per_account(self) -> None:
        async def _run() -> None:
            from openagentic_gateway.channels.manager import ChannelManager
            from openagentic_gateway.channels.registry import ChannelRegistry

            plugin = _FakePlugin()
            reg = ChannelRegistry()
            reg.register(plugin)
            mgr = ChannelManager(registry=reg)

            await mgr.start_channel("fake", account_id="a1")
            await mgr.start_channel("fake", account_id="a1")
            await asyncio.sleep(0)
            self.assertEqual(plugin.started.count("a1"), 1)
            await mgr.stop_channel("fake", account_id="a1")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
