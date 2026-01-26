import unittest


class TestTelegramWebhookContract(unittest.TestCase):
    def test_telegram_update_normalizes_to_inbound_envelope(self) -> None:
        from openagentic_gateway.channels.builtins.telegram_webhook import normalize_telegram_update

        update = {
            "update_id": 1,
            "message": {
                "message_id": 10,
                "chat": {"id": 123, "type": "private"},
                "from": {"id": 456},
                "text": "hello",
            },
        }
        env = normalize_telegram_update(update, account_id="acc1")
        self.assertEqual(env.channel, "telegram")
        self.assertEqual(env.account_id, "acc1")
        self.assertEqual(env.peer_kind, "dm")
        self.assertEqual(env.peer_id, "123")
        self.assertEqual(env.text, "hello")


if __name__ == "__main__":
    unittest.main()

