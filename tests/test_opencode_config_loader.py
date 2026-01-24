import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestOpenCodeConfigLoader(unittest.TestCase):
    def test_discovers_and_merges_config_with_precedence(self) -> None:
        from openagentic_sdk.opencode_config import load_merged_config

        with TemporaryDirectory() as td:
            root = Path(td)
            project = root / "proj" / "subdir"
            project.mkdir(parents=True)

            # Global config (lowest precedence).
            global_dir = root / "global"
            global_dir.mkdir()
            (global_dir / "opencode.json").write_text(
                '{\n'
                '  "model": "global-model",\n'
                '  "instructions": ["global.md"],\n'
                '  "compaction": {"auto": false}\n'
                '}\n',
                encoding="utf-8",
            )
            (global_dir / "global.md").write_text("global-rules", encoding="utf-8")

            # Project config (overrides global).
            (root / "proj" / "opencode.jsonc").write_text(
                "// comment\n{\n  \"model\": \"project-model\",\n  \"instructions\": [\"proj.md\"],\n  \"compaction\": {\"auto\": true, \"prune\": true}\n}\n",
                encoding="utf-8",
            )
            (root / "proj" / "proj.md").write_text("proj-rules", encoding="utf-8")

            # .opencode config (highest precedence).
            (root / "proj" / ".opencode").mkdir()
            (root / "proj" / ".opencode" / "opencode.json").write_text(
                '{"model": "dot-model", "instructions": ["dot.md"]}\n',
                encoding="utf-8",
            )
            (root / "proj" / ".opencode" / "dot.md").write_text("dot-rules", encoding="utf-8")

            cfg = load_merged_config(cwd=str(project), global_config_dir=str(global_dir))
            self.assertEqual(cfg.get("model"), "dot-model")
            # instructions are merged/deduped in order of increasing precedence.
            self.assertEqual(cfg.get("instructions"), ["global.md", "proj.md", "dot.md"])

            comp = cfg.get("compaction")
            self.assertIsInstance(comp, dict)
            self.assertEqual(comp.get("auto"), True)
            self.assertEqual(comp.get("prune"), True)

    def test_jsonc_and_substitutions(self) -> None:
        from openagentic_sdk.opencode_config import load_config_file

        with TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OA_TEST_ENV"] = "ENVVAL"
            try:
                (root / "token.txt").write_text("FILEVAL", encoding="utf-8")
                p = root / "opencode.jsonc"
                p.write_text(
                    """{
  // comment
  "x": "{env:OA_TEST_ENV}",
  "y": "{file:token.txt}",
  "z": "prefix-{env:OA_TEST_ENV}-suffix"
}
""",
                    encoding="utf-8",
                )

                cfg = load_config_file(str(p))
                self.assertEqual(cfg.get("x"), "ENVVAL")
                self.assertEqual(cfg.get("y"), "FILEVAL")
                self.assertEqual(cfg.get("z"), "prefix-ENVVAL-suffix")
            finally:
                os.environ.pop("OA_TEST_ENV", None)


if __name__ == "__main__":
    unittest.main()
