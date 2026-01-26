import unittest


class _GuardDict(dict):
    def __init__(self, lock, *args, **kwargs) -> None:  # noqa: ANN001,ANN002,ANN003
        super().__init__(*args, **kwargs)
        self._lock = lock

    def _assert_locked(self) -> None:
        locked = getattr(self._lock, "locked", None)
        if callable(locked):
            assert locked(), "expected lock to be held"

    def __setitem__(self, key, value) -> None:  # noqa: ANN001,D105
        self._assert_locked()
        return super().__setitem__(key, value)

    def pop(self, key, default=None):  # noqa: ANN001,D102
        self._assert_locked()
        return super().pop(key, default)

    def get(self, key, default=None):  # noqa: ANN001,D102
        self._assert_locked()
        return super().get(key, default)

    def values(self):  # noqa: D102
        self._assert_locked()
        return super().values()


class TestHttpServerPromptQueueThreadSafety(unittest.TestCase):
    def test_prompt_queue_operations_hold_lock(self) -> None:
        from openagentic_sdk.server.http_server import _PromptQueues

        pq = _PromptQueues()
        pq._pending_permissions = _GuardDict(pq._lock)  # noqa: SLF001
        pq._permission_answers = _GuardDict(pq._lock)  # noqa: SLF001
        pq._pending_questions = _GuardDict(pq._lock)  # noqa: SLF001
        pq._question_answers = _GuardDict(pq._lock)  # noqa: SLF001

        perm_q = pq.create_permission("p1", {"id": "p1", "tool": "X"})
        self.assertEqual(pq.list_permissions()[0].get("id"), "p1")
        self.assertTrue(pq.submit_permission_reply("p1", "allow"))
        self.assertEqual(perm_q.get(timeout=0.1), "allow")
        pq.remove_permission("p1")
        self.assertEqual(pq.list_permissions(), [])
        self.assertFalse(pq.submit_permission_reply("missing", "allow"))

        q_q = pq.create_question("q1", {"id": "q1", "prompt": "?"})
        self.assertEqual(pq.list_questions()[0].get("id"), "q1")
        self.assertTrue(pq.submit_question_reply("q1", ["yes"]))
        self.assertEqual(q_q.get(timeout=0.1), ["yes"])
        pq.remove_question("q1")
        self.assertEqual(pq.list_questions(), [])
        self.assertFalse(pq.submit_question_reply("missing", ["x"]))


if __name__ == "__main__":
    unittest.main()

