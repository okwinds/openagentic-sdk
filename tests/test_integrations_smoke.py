from __future__ import annotations

import unittest

from openagentic_sdk.integrations import list_integrations
from openagentic_sdk.integrations.acp import ACPIntegration
from openagentic_sdk.integrations.github import GitHubIntegration
from openagentic_sdk.integrations.slack import SlackIntegration
from openagentic_sdk.integrations.vscode import VSCodeIntegration


class TestIntegrationsSmoke(unittest.TestCase):
    def test_list_integrations(self) -> None:
        items = list_integrations()
        names = {it.name for it in items}
        self.assertTrue({"github", "vscode", "slack", "acp"}.issubset(names))

    def test_github_pr_body_format(self) -> None:
        gh = GitHubIntegration()
        body = gh.format_pull_request_body(summary="x", testing="y")
        self.assertIn("## Summary", body)
        self.assertIn("## Testing", body)

    def test_vscode_hint(self) -> None:
        vs = VSCodeIntegration()
        self.assertIn("VSCode", vs.workspace_hint(project_dir="/tmp"))

    def test_slack_format(self) -> None:
        sl = SlackIntegration()
        self.assertEqual(sl.format_message(text="hi"), "hi")

    def test_acp_protocol_name(self) -> None:
        acp = ACPIntegration()
        self.assertEqual(acp.protocol_name(), "acp")


if __name__ == "__main__":
    unittest.main()
