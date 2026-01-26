import unittest


class TestOpenCodeMarkdownFileRegex(unittest.TestCase):
    def test_matches_same_12_refs_as_opencode(self) -> None:
        from openagentic_sdk.opencode_markdown import files

        template = (
            "This is a @valid/path/to/a/file and it should also match at\n"
            "the beginning of a line:\n\n"
            "@another-valid/path/to/a/file\n\n"
            "but this is not:\n\n"
            '   - Adds a "Co-authored-by:" footer which clarifies which AI agent\n'
            "     helped create this commit, using an appropriate `noreply@...`\n"
            "     or `noreply@anthropic.com` email address.\n\n"
            "We also need to deal with files followed by @commas, ones\n"
            "with @file-extensions.md, even @multiple.extensions.bak,\n"
            "hidden directories like @.config/ or files like @.bashrc\n"
            "and ones at the end of a sentence like @foo.md.\n\n"
            "Also shouldn't forget @/absolute/paths.txt with and @/without/extensions,\n"
            "as well as @~/home-files and @~/paths/under/home.txt.\n\n"
            "If the reference is `@quoted/in/backticks` then it shouldn't match at all."
        )

        matches = files(template)
        self.assertEqual(len(matches), 12)
        self.assertEqual(matches[0], "valid/path/to/a/file")
        self.assertEqual(matches[1], "another-valid/path/to/a/file")
        self.assertEqual(matches[2], "commas")
        self.assertEqual(matches[3], "file-extensions.md")
        self.assertEqual(matches[4], "multiple.extensions.bak")
        self.assertEqual(matches[5], ".config/")
        self.assertEqual(matches[6], ".bashrc")
        self.assertEqual(matches[7], "foo.md")
        self.assertEqual(matches[8], "/absolute/paths.txt")
        self.assertEqual(matches[9], "/without/extensions")
        self.assertEqual(matches[10], "~/home-files")
        self.assertEqual(matches[11], "~/paths/under/home.txt")

    def test_does_not_match_when_preceded_by_backtick(self) -> None:
        from openagentic_sdk.opencode_markdown import files

        self.assertEqual(files("This `@should/not/match` should be ignored"), [])

    def test_does_not_match_email_addresses(self) -> None:
        from openagentic_sdk.opencode_markdown import files

        self.assertEqual(files("Contact user@example.com for help"), [])


if __name__ == "__main__":
    unittest.main()
