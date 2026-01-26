import tempfile
import unittest


class TestSessionMapSqlite(unittest.TestCase):
    def test_get_or_create_persists_across_reopen(self) -> None:
        from openagentic_gateway.sessions.session_map import SessionMap

        with tempfile.TemporaryDirectory() as td:
            path = f"{td}/session_map.sqlite3"
            sm = SessionMap(path=path)
            sid1 = sm.get_or_create(agent_id="agent1", session_key="agent1:telegram:acc:dm:user123")
            sid2 = sm.get_or_create(agent_id="agent1", session_key="agent1:telegram:acc:dm:user123")
            self.assertEqual(sid1, sid2)
            sm.close()

            sm2 = SessionMap(path=path)
            sid3 = sm2.get_or_create(agent_id="agent1", session_key="agent1:telegram:acc:dm:user123")
            self.assertEqual(sid1, sid3)
            sid_other = sm2.get_or_create(agent_id="agent1", session_key="agent1:telegram:acc:group:group999")
            self.assertNotEqual(sid1, sid_other)
            sm2.close()


if __name__ == "__main__":
    unittest.main()

