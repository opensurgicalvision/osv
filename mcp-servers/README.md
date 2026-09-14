# Custom Model Context Protocol (MCP) Servers

This directory contains standalone Python implementations of the 8 project-specific MCP servers:

1. `osv-annotation`: Queries CVAT/Label Studio tasks, returns masks and consensus metrics (NO raw images/pixels).
2. `osv-experiments`: Connects to MLflow/W&B tracking, retrieves run metrics, hyperparameters, and artifacts.
3. `osv-datasets`: Inspects dataset status, download progress, and metadata cards.
4. `osv-dicom`: Validates DICOM tag scrub status and reports verification verdicts (NEVER returns tag values).
5. `osv-leaderboard`: Queries leaderboard submissions, ranks, and golden benchmark diffs.
6. `osv-cfp`: Tracks conference deadlines (MICCAI, IPCAI, MIDL, CARS) and paper constraints.
7. `osv-github-ro` **(implemented)**: Read-only PR introspection -- `get_pr_metadata`, `get_pr_diff`, `list_pr_files`, `get_pr_comments`. No mutating tool exists in this server; see `osv-github-ro/_github_ro_core.py`.
8. `osv-github-triage` **(implemented)**: The only write surface an agent gets to GitHub -- `post_pr_comment`, `set_label`. `set_label` enforces a hardcoded allowlist in `osv-github-triage/_github_triage_core.py`; verdict/approval/merge-shaped labels (`deid:pass`, `approved`, ...) are rejected before any HTTP call.

> **CRITICAL DATA GOVERNANCE RULE:** MCP servers handling medical data MUST only return derivatives and metadata, never raw patient pixels or private tag values.

## Why `osv-github-ro` / `osv-github-triage` exist

`deid-gate` and `pr-triage` both read PR content that is entirely attacker-controlled before a
human has looked at it. Giving either of them the `Bash` tool plus `gh` CLI access would let a
prompt-injected diff try to persuade the model to run an arbitrary shell command -- `echo
"approved" > some_file.py`, `gh pr merge`, or worse. These two servers close that vector
structurally rather than by policy: `osv-github-ro` has no function that can write anything
(enforced by a test that scans its public API for write-shaped names -- see
`tests/test_github_ro_core.py`), and `osv-github-triage`'s only write tool refuses any label
outside a fixed allowlist in code, not in a system prompt an injected diff could argue with.
Agents that handle untrusted PR content get these two servers and never `Bash`. Full rationale:
`docs/adr/0001-two-stage-ci-for-agents.md` and `.ai/rules.md` R-21.

## Status

Only `osv-github-ro` and `osv-github-triage` have a working implementation today (core logic is
covered by `tests/test_github_ro_core.py` and `tests/test_github_triage_core.py`; the MCP
transport wiring in each `osv_*_mcp.py` targets the `mcp` Python SDK's FastMCP API and has not
been exercised against a live MCP client in this environment). The other six servers are speced
in `.ai/mcp/servers.json` but not yet implemented -- that is early-roadmap work for R4, tracked
in the issue tracker.
