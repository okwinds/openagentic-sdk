from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class GithubRunInputs:
    event: Mapping[str, Any]
    event_name: str
    repository: str
    run_id: str


@dataclass(frozen=True, slots=True)
class GithubTarget:
    owner: str
    repo: str
    issue_number: int


def _read_json_file(path: str) -> dict[str, Any]:
    p = Path(path)
    obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    return obj if isinstance(obj, dict) else {}


def derive_prompt_from_github_event(inp: GithubRunInputs) -> str:
    # Very small, best-effort prompt derivation. This is enough for local
    # validation + gives us a stable unit-test surface.
    env_prompt = (os.environ.get("PROMPT") or "").strip()

    if inp.event_name in {"schedule", "workflow_dispatch"}:
        if not env_prompt:
            raise SystemExit("Missing PROMPT for schedule/workflow_dispatch")
        return env_prompt

    if inp.event_name == "issue_comment":
        comment: dict[str, Any] = {}
        comment_raw = inp.event.get("comment")
        if isinstance(comment_raw, dict):
            comment = dict(comment_raw)

        issue: dict[str, Any] = {}
        issue_raw = inp.event.get("issue")
        if isinstance(issue_raw, dict):
            issue = dict(issue_raw)
        body = str(comment.get("body") or "").strip()
        title = str(issue.get("title") or "").strip()
        url = str(issue.get("html_url") or "").strip()
        base = f"GitHub issue comment on {inp.repository}"
        if title:
            base += f"\nIssue: {title}"
        if url:
            base += f"\nURL: {url}"
        if body:
            base += f"\n\nComment:\n{body}"
        if env_prompt:
            base += f"\n\nPROMPT override:\n{env_prompt}"
        return base.strip()

    if inp.event_name == "issues":
        issue: dict[str, Any] = {}
        issue_raw = inp.event.get("issue")
        if isinstance(issue_raw, dict):
            issue = dict(issue_raw)
        title = str(issue.get("title") or "").strip()
        body = str(issue.get("body") or "").strip()
        url = str(issue.get("html_url") or "").strip()
        base = f"GitHub issue event on {inp.repository}"
        if title:
            base += f"\nTitle: {title}"
        if url:
            base += f"\nURL: {url}"
        if body:
            base += f"\n\nBody:\n{body}"
        if env_prompt:
            base += f"\n\nPROMPT override:\n{env_prompt}"
        return base.strip()

    if inp.event_name == "pull_request":
        pr: dict[str, Any] = {}
        pr_raw = inp.event.get("pull_request")
        if isinstance(pr_raw, dict):
            pr = dict(pr_raw)
        title = str(pr.get("title") or "").strip()
        body = str(pr.get("body") or "").strip()
        url = str(pr.get("html_url") or "").strip()
        base = f"GitHub pull_request event on {inp.repository}"
        if title:
            base += f"\nTitle: {title}"
        if url:
            base += f"\nURL: {url}"
        if body:
            base += f"\n\nBody:\n{body}"
        if env_prompt:
            base += f"\n\nPROMPT override:\n{env_prompt}"
        return base.strip()

    # Fallback.
    if env_prompt:
        return env_prompt
    raise SystemExit(f"Unsupported event: {inp.event_name}; set PROMPT")


def should_respond_to_comment(*, body: str, mentions_csv: str) -> bool:
    body_l = (body or "").lower()
    mentions = [m.strip().lower() for m in (mentions_csv or "").split(",") if m.strip()]
    if not mentions:
        return True
    return any(m in body_l for m in mentions)


def _parse_repo(repo_full: str) -> tuple[str, str]:
    s = (repo_full or "").strip()
    if "/" not in s:
        raise SystemExit("Invalid GITHUB_REPOSITORY; expected owner/repo")
    owner, name = s.split("/", 1)
    if not owner or not name:
        raise SystemExit("Invalid GITHUB_REPOSITORY; expected owner/repo")
    return owner, name


def _extract_issue_number(inp: GithubRunInputs) -> int | None:
    if inp.event_name == "issue_comment":
        issue: dict[str, Any] = {}
        issue_raw = inp.event.get("issue")
        if isinstance(issue_raw, dict):
            issue = dict(issue_raw)
        n = issue.get("number")
        return int(n) if isinstance(n, int) and n > 0 else None
    if inp.event_name == "issues":
        issue: dict[str, Any] = {}
        issue_raw = inp.event.get("issue")
        if isinstance(issue_raw, dict):
            issue = dict(issue_raw)
        n = issue.get("number")
        return int(n) if isinstance(n, int) and n > 0 else None
    if inp.event_name == "pull_request":
        pr: dict[str, Any] = {}
        pr_raw = inp.event.get("pull_request")
        if isinstance(pr_raw, dict):
            pr = dict(pr_raw)
        n = pr.get("number")
        return int(n) if isinstance(n, int) and n > 0 else None
    return None


def resolve_target(inp: GithubRunInputs) -> GithubTarget | None:
    n = _extract_issue_number(inp)
    if n is None:
        return None
    owner, repo = _parse_repo(inp.repository)
    return GithubTarget(owner=owner, repo=repo, issue_number=n)


def post_issue_comment(*, base_url: str, token: str, target: GithubTarget, body: str) -> dict[str, Any]:
    url = base_url.rstrip("/") + f"/repos/{target.owner}/{target.repo}/issues/{target.issue_number}/comments"
    payload = json.dumps({"body": body}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        method="POST",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "openagentic-sdk",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
        raw = resp.read()
    obj = json.loads(raw.decode("utf-8", errors="replace"))
    return obj if isinstance(obj, dict) else {}


def cmd_github_install(*, workflow_path: str | None, force: bool) -> str:
    root = Path.cwd()
    rel = workflow_path or os.fspath(Path(".github") / "workflows" / "openagentic.yml")
    p = Path(rel)
    if p.is_absolute():
        # Keep install deterministic and safe for users running in a repo.
        raise SystemExit("--path must be relative")
    full = (root / p).resolve()
    if root.resolve() not in full.parents and full != root.resolve():
        raise SystemExit("--path must be within the current working directory")
    full.parent.mkdir(parents=True, exist_ok=True)
    if full.exists() and not force:
        raise SystemExit(f"Refusing to overwrite existing file: {p} (use --force)")

    # Minimal workflow that runs `oa github run`. Users can tune permissions.
    text = """name: OpenAgentic

on:
  workflow_dispatch:
    inputs:
      prompt:
        description: 'Prompt to run'
        required: true
        type: string
  schedule:
    - cron: '0 0 * * *'
  issue_comment:
    types: [created]

jobs:
  run:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install openagentic-sdk
        run: pip install -U openagentic-sdk
      - name: Run
        env:
          PROMPT: ${{ github.event.inputs.prompt }}
          GITHUB_EVENT_NAME: ${{ github.event_name }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          GITHUB_RUN_ID: ${{ github.run_id }}
          GITHUB_EVENT_PATH: ${{ github.event_path }}
          RIGHTCODE_API_KEY: ${{ secrets.RIGHTCODE_API_KEY }}
        run: oa github run
"""
    full.write_text(text, encoding="utf-8")
    return os.fspath(p)


def cmd_github_run(*, event_path: str | None, print_prompt: bool) -> str:
    path = event_path or os.environ.get("GITHUB_EVENT_PATH")
    if not path:
        raise SystemExit("Missing --event-path (or set GITHUB_EVENT_PATH)")
    event = _read_json_file(path)

    event_name = (os.environ.get("GITHUB_EVENT_NAME") or "").strip() or "unknown"
    repo = (os.environ.get("GITHUB_REPOSITORY") or "").strip() or "unknown/unknown"
    run_id = (os.environ.get("GITHUB_RUN_ID") or "").strip() or ""

    inp = GithubRunInputs(event=event, event_name=event_name, repository=repo, run_id=run_id)

    mentions = (os.environ.get("MENTIONS") or "/opencode,/oc").strip()
    if event_name == "issue_comment" and not print_prompt:
        comment: dict[str, Any] = {}
        comment_raw = event.get("comment")
        if isinstance(comment_raw, dict):
            comment = dict(comment_raw)
        body = str(comment.get("body") or "")
        if not should_respond_to_comment(body=body, mentions_csv=mentions):
            return "skipped"

    prompt = derive_prompt_from_github_event(inp)
    if print_prompt:
        return prompt

    # Allow offline testing: if reply text is injected, skip running the agent.
    reply_text = (os.environ.get("OA_GITHUB_REPLY_TEXT") or "").strip()
    if reply_text:
        reply = reply_text
    else:
        from .config import build_options
        import asyncio
        from openagentic_sdk import run as oa_run

        cwd = os.getcwd()
        # Default to plan mode in CI to avoid hanging on non-interactive approvals.
        permission_mode = (os.environ.get("OA_GITHUB_PERMISSION_MODE") or os.environ.get("OA_PERMISSION_MODE") or "plan").strip()
        opts = build_options(cwd=cwd, project_dir=cwd, permission_mode=permission_mode, interactive=False)
        res = asyncio.run(oa_run(prompt=prompt, options=opts))
        reply = res.final_text

    # Best-effort posting to GitHub.
    token = (os.environ.get("GITHUB_TOKEN") or "").strip()
    base_url = (os.environ.get("GITHUB_API_URL") or "https://api.github.com").strip()
    target = resolve_target(inp)
    if not token or target is None:
        return reply
    _ = post_issue_comment(base_url=base_url, token=token, target=target, body=reply)
    return reply
