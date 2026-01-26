import unittest


class TestReplyPromptRendering(unittest.TestCase):
    def test_envelope_renders_channel_and_peer(self) -> None:
        from openagentic_gateway.reply.envelope import InboundEnvelope, render_prompt

        env = InboundEnvelope(
            channel="telegram",
            account_id="acc",
            peer_kind="dm",
            peer_id="user123",
            text="hello",
        )
        prompt = render_prompt(env)
        self.assertIn("channel=telegram", prompt)
        self.assertIn("peer=dm:user123", prompt)
        self.assertIn("hello", prompt)


if __name__ == "__main__":
    unittest.main()

