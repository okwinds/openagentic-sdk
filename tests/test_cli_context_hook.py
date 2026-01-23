import unittest
import os


class TestCliContextHook(unittest.TestCase):
    def test_cli_context_injected_once(self) -> None:
        from open_agent_cli.config import build_options

        os.environ["RIGHTCODE_API_KEY"] = "x"
        try:
            opts = build_options(
                cwd="C:\\proj",
                project_dir="C:\\proj",
                permission_mode="deny",
                interactive=False,
            )
        finally:
            os.environ.pop("RIGHTCODE_API_KEY", None)

        msgs = [{"role": "system", "content": "BASE"}, {"role": "user", "content": "hi"}]
        out1, _, _ = self._run_before_model_call(opts, msgs)
        out2, _, _ = self._run_before_model_call(opts, out1)

        self.assertTrue(isinstance(out1[0].get("content"), str))
        self.assertIn("## OA CLI Context", out1[0]["content"])
        self.assertIn("cwd: C:\\proj", out1[0]["content"])
        self.assertIn("authoritative", out1[0]["content"])
        self.assertEqual(out1[0]["content"].count("## OA CLI Context"), 1)
        self.assertEqual(out2[0]["content"].count("## OA CLI Context"), 1)

    def _run_before_model_call(self, opts, msgs):  # noqa: ANN001
        import asyncio

        return asyncio.run(opts.hooks.run_before_model_call(messages=msgs, context={"model": "gpt-5.2"}))


if __name__ == "__main__":
    unittest.main()
