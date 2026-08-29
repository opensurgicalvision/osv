"""Unit tests for the osv-github-ro MCP server's core logic.

No network, no `mcp`/`httpx` package needed -- the module under test has no
external dependencies at all, which is itself part of what makes it safe to
put in front of untrusted PR content.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "mcp-servers" / "osv-github-ro"))

import _github_ro_core as core  # noqa: E402


class FakeResponse:
    def __init__(self, json_data=None, text_data=""):
        self._json = json_data
        self.text = text_data

    def json(self):
        return self._json


def test_get_pr_metadata_shapes_response():
    fake_pr = {
        "number": 42,
        "title": "Add CholecSeg8k loader",
        "body": "Fixes #7",
        "user": {"login": "alice"},
        "author_association": "FIRST_TIME_CONTRIBUTOR",
        "base": {"ref": "main"},
        "head": {"ref": "alice/cholecseg8k"},
        "labels": [{"name": "needs-tests"}],
        "draft": False,
    }
    calls = []

    def fake_get(url, headers):
        calls.append((url, headers))
        return FakeResponse(json_data=fake_pr)

    result = core.get_pr_metadata(fake_get, "tok", "org", "repo", 42)

    assert result["number"] == 42
    assert result["author"] == "alice"
    assert result["labels"] == ["needs-tests"]
    assert calls[0][0].endswith("/repos/org/repo/pulls/42")
    assert calls[0][1]["Authorization"] == "Bearer tok"


def test_get_pr_diff_requests_diff_media_type():
    captured_headers = {}

    def fake_get(url, headers):
        captured_headers.update(headers)
        return FakeResponse(text_data="diff --git a/x b/x\n+evil")

    result = core.get_pr_diff(fake_get, "tok", "org", "repo", 1)

    assert result == "diff --git a/x b/x\n+evil"
    assert captured_headers["Accept"] == "application/vnd.github.v3.diff"


def test_list_pr_files_shapes_each_entry():
    def fake_get(url, headers):
        return FakeResponse(
            json_data=[
                {"filename": "osv/datasets/loader.py", "status": "added", "additions": 40, "deletions": 0}
            ]
        )

    result = core.list_pr_files(fake_get, "tok", "org", "repo", 1)

    assert result == [
        {"path": "osv/datasets/loader.py", "status": "added", "additions": 40, "deletions": 0}
    ]


def test_get_pr_comments_shapes_each_entry():
    def fake_get(url, headers):
        return FakeResponse(
            json_data=[{"user": {"login": "bob"}, "body": "lgtm", "created_at": "2026-08-01T00:00:00Z"}]
        )

    result = core.get_pr_comments(fake_get, "tok", "org", "repo", 1)

    assert result == [{"author": "bob", "body": "lgtm", "created_at": "2026-08-01T00:00:00Z"}]


def test_module_exposes_no_write_shaped_function():
    """The actual security property: scan the module's public names for
    anything that looks like it could mutate GitHub state, and fail loudly
    if one ever gets added without a matching review of this test."""
    write_shaped_prefixes = ("post_", "set_", "delete_", "merge_", "close_", "edit_", "update_", "create_")
    public_names = [name for name in dir(core) if not name.startswith("_")]
    offenders = [n for n in public_names if n.lower().startswith(write_shaped_prefixes)]
    assert offenders == [], f"osv-github-ro must stay read-only; found write-shaped names: {offenders}"
