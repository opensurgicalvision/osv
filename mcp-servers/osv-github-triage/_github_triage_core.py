"""Pure, testable GitHub write logic for the osv-github-triage MCP server.

This is the *only* MCP surface in the project that lets an agent write to
GitHub, and it is deliberately narrow: two operations, and one hardcoded
label allowlist enforced here in code -- not in a prompt, not in a review
guideline an agent could be talked out of. A prompt-injected diff can ask
this tool for anything it likes; the tool itself refuses anything outside
the allowlist before a single HTTP request is made.

Kept separate from the MCP transport wiring (osv_github_triage_mcp.py) so
this logic -- the actual security boundary -- is unit-testable without a
running MCP server, a network connection, or the `mcp`/`httpx` packages.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

GITHUB_API = "https://api.github.com"

# R-10 / R-19 / R-20 (.ai/rules.md): agents never set a verdict, merge, or
# approval-shaped label, and never touch the automation-bias control-frame
# mechanism. Verdict labels like deid:pass / deid:fail are written directly
# by the deterministic Stage A job, which has no LLM in its loop at all --
# never by this server, and never by an agent holding it.
ALLOWED_LABELS = frozenset(
    {
        "needs-tests",
        "needs-clinician",
        "needs-rebase",
        "first-contribution",
        "automation-bias",
        "repro-failure",
    }
)


class LabelNotAllowed(ValueError):
    """Raised when an agent asks for a label outside ALLOWED_LABELS.

    This is the mechanical half of the boundary described in every triage
    agent's Hard Boundaries section -- a policy stated only in a system
    prompt can be argued around by a sufficiently clever injected diff; a
    raised exception in the tool implementation cannot.
    """


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def post_pr_comment(
    post: Callable[..., Any], token: str, owner: str, repo: str, pr_number: int, body: str
) -> dict[str, Any]:
    """Post a single comment on a pull request. Refuses an empty body rather
    than silently no-op-ing, so a bug upstream is visible immediately."""
    if not body.strip():
        raise ValueError("refusing to post an empty PR comment")
    resp = post(
        f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
        headers=_headers(token),
        json={"body": body},
    )
    data = resp.json()
    return {"comment_id": data["id"], "url": data["html_url"]}


def set_label(
    post: Callable[..., Any], token: str, owner: str, repo: str, pr_number: int, label: str
) -> dict[str, Any]:
    """Apply one informational label from ALLOWED_LABELS. Raises LabelNotAllowed
    for anything else -- including deid:pass, deid:fail, approved, lgtm, or any
    label an injected diff might ask for by name."""
    if label not in ALLOWED_LABELS:
        raise LabelNotAllowed(
            f"'{label}' is not on the agent-writable label allowlist "
            f"{sorted(ALLOWED_LABELS)}. Verdict, merge, and approval labels are "
            "written only by deterministic, secret-free CI steps -- never by an agent."
        )
    resp = post(
        f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/labels",
        headers=_headers(token),
        json={"labels": [label]},
    )
    return {"labels": resp.json()}
