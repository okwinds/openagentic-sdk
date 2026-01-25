import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestOpenCodeConfigLoader(unittest.TestCase):
    def test_project_config_precedence_json_over_jsonc(self) -> None:
        """OpenCode loads opencode.jsonc then opencode.json (json wins)."""

        from openagentic_sdk.opencode_config import load_merged_config

        with TemporaryDirectory() as td:
            root = Path(td)
            project = root / "proj" / "subdir"
            project.mkdir(parents=True)

            os.environ["OPENCODE_TEST_HOME"] = str(root / "home")
            try:
                (root / "proj" / "opencode.jsonc").write_text('{"model": "jsonc"}\n', encoding="utf-8")
                (root / "proj" / "opencode.json").write_text('{"model": "json"}\n', encoding="utf-8")

                cfg = load_merged_config(cwd=str(project), global_config_dir=str(root / "empty-global"))
                self.assertEqual(cfg.get("model"), "json")
            finally:
                os.environ.pop("OPENCODE_TEST_HOME", None)

    def test_jsonc_and_substitutions_match_opencode(self) -> None:
        from openagentic_sdk.opencode_config import load_config_file

        with TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OA_TEST_ENV"] = "ENVVAL"
            try:
                (root / "token.txt").write_text('A "B"\nC', encoding="utf-8")
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
                self.assertEqual(cfg.get("y"), 'A "B"\nC')
                self.assertEqual(cfg.get("z"), "prefix-ENVVAL-suffix")
            finally:
                os.environ.pop("OA_TEST_ENV", None)

    def test_file_substitution_missing_raises_but_commented_is_skipped(self) -> None:
        from openagentic_sdk.opencode_config import load_config_file

        with TemporaryDirectory() as td:
            root = Path(td)
            p1 = root / "bad.jsonc"
            p1.write_text('{"x": "{file:missing.txt}"}\n', encoding="utf-8")
            with self.assertRaises(Exception):
                _ = load_config_file(str(p1))

            # Commented-out file token should not trigger substitution errors.
            p2 = root / "ok.jsonc"
            p2.write_text(
                """{
  // \"y\": \"{file:missing.txt}\",
  "x": 1
}
""",
                encoding="utf-8",
            )
            cfg = load_config_file(str(p2))
            self.assertEqual(cfg.get("x"), 1)
            self.assertNotIn("y", cfg)

    def test_merge_semantics_only_plugin_and_instructions_concat(self) -> None:
        from openagentic_sdk.opencode_config import load_merged_config

        with TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OPENCODE_TEST_HOME"] = str(root / "home")
            try:
                global_dir = root / "global"
                global_dir.mkdir(parents=True)
                (global_dir / "opencode.json").write_text(
                    '{"x": [1], "instructions": ["a"], "plugin": ["p1"]}\n',
                    encoding="utf-8",
                )

                project = root / "proj" / "sub"
                project.mkdir(parents=True)
                (root / "proj" / "opencode.json").write_text(
                    '{"x": [2], "instructions": ["b"], "plugin": ["p2"]}\n',
                    encoding="utf-8",
                )

                cfg = load_merged_config(cwd=str(project), global_config_dir=str(global_dir))
                self.assertEqual(cfg.get("x"), [2])
                self.assertEqual(cfg.get("instructions"), ["a", "b"])
                self.assertEqual(cfg.get("plugin"), ["p1", "p2"])
            finally:
                os.environ.pop("OPENCODE_TEST_HOME", None)



if __name__ == "__main__":
    unittest.main()
