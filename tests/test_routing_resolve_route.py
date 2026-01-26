import unittest


class TestRoutingResolveRoute(unittest.TestCase):
    def test_session_key_is_deterministic_for_dm_and_group(self) -> None:
        from openagentic_gateway.routing.resolve_route import resolve_route

        dm = resolve_route(
            agent_id="agent1",
            channel="telegram",
            account_id="acc",
            peer_kind="dm",
            peer_id="user123",
        )
        dm2 = resolve_route(
            agent_id="agent1",
            channel="telegram",
            account_id="acc",
            peer_kind="dm",
            peer_id="user123",
        )
        grp = resolve_route(
            agent_id="agent1",
            channel="telegram",
            account_id="acc",
            peer_kind="group",
            peer_id="group999",
        )

        self.assertEqual(dm.session_key, dm2.session_key)
        self.assertNotEqual(dm.session_key, grp.session_key)
        self.assertEqual(dm.session_key, dm.session_key.lower())


if __name__ == "__main__":
    unittest.main()

