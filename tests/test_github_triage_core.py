"""Unit tests for the osv-github-triage MCP server's core logic.

The label allowlist enforcement here IS the security boundary described in
every triage agent's Hard Boundaries section (deid:pass/deid:fail can only be
set by the deterministic Stage A job). These tests exist to prove that
boundary is code, not just prose an agent could be argued around.
"""

import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "mcp-servers" / "osv-github-triage"))

import _github_triage_core as core  # noqa: E402


class FakeResponse:
    def __init__(self, json_data=None):
        self._json = json_data

    def json(self):
        return self._json


def test_post_pr_comment_happy_path():
    calls = []

    def fake_post(url, headers, json):
        calls.append((url, headers, json))
        return FakeResponse(json_data={"id": 999, "html_url": "https://github.com/o/r/pull/1#issuecomment-999"})

    result = core.post_pr_comment(fake_post, "tok", "org", "repo", 1, "Looks good, one nit.")

    assert result["comment_id"] == 999
    assert calls[0][2] == {"body": "Looks good, one nit."}


def test_post_pr_comment_refuses_empty_body():
    def fake_post(url, headers, json):
        raise AssertionError("must not reach the network for an empty comment")

    with pytest.raises(ValueError, match="empty"):
        core.post_pr_comment(fake_post, "tok", "org", "repo", 1, "   ")


@pytest.mark.parametrize("label", sorted(core.ALLOWED_LABELS))
def test_set_label_allows_every_listed_label(label):
    def fake_post(url, headers, json):
        assert json == {"labels": [label]}
        return FakeResponse(json_data=[{"name": label}])

    result = core.set_label(fake_post, "tok", "org", "repo", 1, label)
    assert result["labels"] == [{"name": label}]


@pytest.mark.parametrize(
    "forbidden_label",
    [
        "deid:pass",
        "deid:fail",
        "approved",
        "lgtm",
        "merge",
        "hacktoberfest-accepted",
        "pre-approved",
        "trivial",
    ],
)
def test_set_label_rejects_verdict_and_approval_labels(forbidden_label):
    """These are exactly the labels a prompt-injected diff would ask for:
    the deid verdict, an approval signal, or a self-granted merge exemption.
    Each must be rejected before any HTTP call is made."""

    def fake_post(url, headers, json):
        raise AssertionError(f"must not reach the network for disallowed label '{forbidden_label}'")

    with pytest.raises(core.LabelNotAllowed):
        core.set_label(fake_post, "tok", "org", "repo", 1, forbidden_label)


def test_module_has_no_merge_or_push_shaped_function():
    forbidden_prefixes = ("merge_", "push_", "delete_", "close_issue", "edit_file", "write_file")
    public_names = [name for name in dir(core) if not name.startswith("_")]
    offenders = [n for n in public_names if n.lower().startswith(forbidden_prefixes)]
    assert offenders == [], f"osv-github-triage must never grow a merge/push tool; found: {offenders}"
