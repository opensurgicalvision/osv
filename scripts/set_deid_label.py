"""Sets the deid:pass / deid:fail verdict label directly from deid-verdict.json.

Deliberately separate from mcp-servers/osv-github-triage/_github_triage_core.py's
set_label(): that function's ALLOWED_LABELS allowlist explicitly EXCLUDES verdict
labels, because an LLM agent must never set them. This script IS the trusted,
non-agent, deterministic caller that is allowed to -- reusing the agent-facing
function here would be reusing the wrong permission boundary, not the right code.

Runs as a plain CI step with no LLM secret involved (R-09 in .ai/rules.md), which
is what lets it run on a fork's pull request at all.
"""

from __future__ import annotations

import json
import os
import sys

# httpx is imported inside main() on purpose: label_for() is the part worth
# unit-testing, and tests/test_set_deid_label.py must be able to import it in a
# bare environment with no HTTP client installed -- the same reason the MCP core
# modules keep their transport out of import scope.

GITHUB_API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
VERDICT_LABELS = ("deid:pass", "deid:fail")


def label_for(verdict: dict) -> str:
    return "deid:pass" if verdict.get("overall") == "pass" else "deid:fail"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: set_deid_label.py <deid-verdict.json>", file=sys.stderr)
        return 2

    token = os.environ.get("GITHUB_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    pr_number = os.environ.get("PR_NUMBER", "")
    if not (token and repository and pr_number):
        print("set_deid_label: missing GITHUB_REPOSITORY/PR_NUMBER/GITHUB_TOKEN; skipping")
        return 0

    import httpx

    verdict = json.loads(open(sys.argv[1], encoding="utf-8").read())
    new_label = label_for(verdict)
    other_label = next(label for label in VERDICT_LABELS if label != new_label)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    issue_url = f"{GITHUB_API}/repos/{repository}/issues/{pr_number}"

    resp = httpx.post(
        f"{issue_url}/labels", headers=headers, json={"labels": [new_label]}, timeout=15.0
    )
    resp.raise_for_status()

    # Removing a label the PR does not carry is a 404, not a failure: the
    # steady state we want is "exactly one verdict label", and on the first
    # run there is nothing to remove.
    removal = httpx.delete(f"{issue_url}/labels/{other_label}", headers=headers, timeout=15.0)
    if removal.status_code not in (200, 404):
        removal.raise_for_status()

    print(f"set_deid_label: applied '{new_label}' (removed '{other_label}')")
    return 0


if __name__ == "__main__":
    sys.exit(main())
