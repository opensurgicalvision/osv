"""Pure, testable GitHub read logic for the osv-github-ro MCP server.

Kept separate from the MCP transport wiring (osv_github_ro_mcp.py) so the
GitHub API logic is unit-testable without a running MCP server, a network
connection, or the `mcp`/`httpx` packages installed at all.

The security property this module exists for: every function here issues
exactly one HTTP GET and returns data. There is no function that could write,
delete, merge, or push anything -- not "we didn't wire up a mutating tool",
but "there is no mutating code in this file to wire up." Agents that read
untrusted PR content (deid-gate, pr-triage) get this server and never get the
Bash tool, so a prompt-injected diff has no shell to reach for and no
write-shaped function to call even if it tried (see .ai/rules.md R-21 and
docs/adr/0001-two-stage-ci-for-agents.md).
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

GITHUB_API = "https://api.github.com"


class HttpGet(Protocol):
    """A GET-only HTTP call. Anything satisfying this (e.g. httpx.get) works;
    nothing satisfying it can also POST/PATCH/DELETE by construction."""

    def __call__(self, url: str, headers: dict[str, str]) -> Any: ...


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_pr_metadata(get: HttpGet, token: str, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
    """Title, author, base/head branches, labels, and body of a pull request."""
    resp = get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}", headers=_headers(token))
    data = resp.json()
    return {
        "number": data["number"],
        "title": data["title"],
        "body": data.get("body") or "",
        "author": data["user"]["login"],
        "author_association": data.get("author_association"),
        "base": data["base"]["ref"],
        "head": data["head"]["ref"],
        "labels": [label["name"] for label in data.get("labels", [])],
        "draft": data.get("draft", False),
    }


def get_pr_diff(get: HttpGet, token: str, owner: str, repo: str, pr_number: int) -> str:
    """Unified diff of a pull request. The caller must treat the returned text
    as untrusted -- it is authored entirely by the PR's submitter."""
    headers = _headers(token)
    headers["Accept"] = "application/vnd.github.v3.diff"
    resp = get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}", headers=headers)
    return resp.text


def list_pr_files(get: HttpGet, token: str, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
    """Changed files in a pull request with add/delete counts and status."""
    resp = get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files", headers=_headers(token))
    return [
        {
            "path": f["filename"],
            "status": f["status"],
            "additions": f["additions"],
            "deletions": f["deletions"],
        }
        for f in resp.json()
    ]


def get_pr_comments(get: HttpGet, token: str, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
    """Existing comment thread on a pull request (issue-comments endpoint,
    which is where PR-level comments -- as opposed to inline review comments
    -- live in the GitHub API)."""
    resp = get(f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments", headers=_headers(token))
    return [
        {"author": c["user"]["login"], "body": c["body"], "created_at": c["created_at"]}
        for c in resp.json()
    ]
