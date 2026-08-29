# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.0.0", "httpx>=0.27.0"]
# ///
"""osv-github-triage MCP server -- the only GitHub write surface an agent gets.

Two tools: post_pr_comment, set_label. set_label enforces a hardcoded label
allowlist in _github_triage_core.py -- an agent cannot set deid:pass,
deid:fail, approved, or any label outside that set, because the tool itself
raises before making the HTTP call, not because a prompt asked it not to.

There is no merge, push, close, or file-edit tool anywhere in this server.
Agents that need to act on a PR (deid-gate, pr-triage, newcomer-greeter) get
this server plus osv-github-ro for reading, and never the Bash tool.

Run via: uv run --directory mcp-servers/osv-github-triage osv_github_triage_mcp.py

NOTE: written against the FastMCP high-level API (`mcp.server.fastmcp`) from
the official `mcp` Python SDK. If your installed SDK version's decorator or
`run()` signature differs, only this wiring file needs adjusting -- the write
logic and label allowlist in _github_triage_core.py have no dependency on
`mcp` at all and are unit-tested independently (see
tests/test_github_triage_core.py).
"""

from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP

import _github_triage_core as core

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]  # supplied only by the Stage B workflow

mcp = FastMCP("osv-github-triage")


def _post(url: str, headers: dict[str, str], json: dict) -> httpx.Response:
    response = httpx.post(url, headers=headers, json=json, timeout=15.0)
    response.raise_for_status()
    return response


@mcp.tool()
def post_pr_comment(owner: str, repo: str, pr_number: int, body: str) -> dict:
    """Post a single comment on a pull request."""
    return core.post_pr_comment(_post, GITHUB_TOKEN, owner, repo, pr_number, body)


@mcp.tool()
def set_label(owner: str, repo: str, pr_number: int, label: str) -> dict:
    """Apply one informational label. Only labels in the allowlist in
    _github_triage_core.ALLOWED_LABELS are accepted; anything else raises."""
    return core.set_label(_post, GITHUB_TOKEN, owner, repo, pr_number, label)


if __name__ == "__main__":
    mcp.run()
