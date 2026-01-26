import unittest


class _Plugin:
    def __init__(self, plugin_id: str, *, aliases: list[str] | None = None) -> None:
        self.id = plugin_id
        self.meta = type("Meta", (), {"aliases": aliases or []})


class TestChannelsRegistry(unittest.TestCase):
    def test_registry_preserves_order_and_resolves_aliases(self) -> None:
        from openagentic_gateway.channels.registry import ChannelRegistry

        reg = ChannelRegistry()
        a = _Plugin("telegram", aliases=["tg"])
        b = _Plugin("slack", aliases=["slk"])
        reg.register(a)
        reg.register(b)

        self.assertEqual([p.id for p in reg.list_plugins()], ["telegram", "slack"])
        self.assertIs(reg.get("telegram"), a)
        self.assertIs(reg.get("tg"), a)
        self.assertIs(reg.get("slk"), b)
        self.assertIsNone(reg.get("unknown"))


if __name__ == "__main__":
    unittest.main()

