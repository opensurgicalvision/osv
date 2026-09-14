"""Test that osv.demo is the single legitimate path to a rendered clip (R-01, R-26).

Same shape as test_demo_guard.py: the refusals and the allowed calls carry equal
weight, because a renderer that blocks a legitimate demo gets replaced by a
hand-rolled ffmpeg line, and that line has none of the guarantees.

The five checks below the divider started as `xfail(strict=True)` markers pinning
defects found in review - allowlist format, the hook/CLI deadlock, the output-path
predicate, filtergraph injection through the run id, and frame containment. They
are plain tests now that those are fixed, and they stay to keep them fixed.

Nothing here invokes ffmpeg: every test stops at a validation boundary, so the
suite stays runnable on a machine with no ffmpeg installed (which is currently
every machine in this project).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
HOOK = ROOT_DIR / ".ai" / "hooks" / "demo_guard.py"
ALLOWLIST = ROOT_DIR / "demo-assets" / "allowlist.yaml"

sys.path.insert(0, str(ROOT_DIR))

from osv.demo.__main__ import (  # noqa: E402
    SecurityError,
    load_allowlist,
    validate_and_resolve_frames,
    verify_output_location,
)

# The invocation the agent is documented to use, as one argv list.
CANONICAL_ARGS = [
    "--run-id", "mlflow-run-abc12345",
    "--frame-list", "/tmp/frames_to_render.txt",
    "--output", "/tmp/demo-artifacts/run_abc12345.mp4",
    "--fps", "10",
]


def run_module(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "osv.demo", *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT_DIR),
    )


def run_hook(command: str) -> subprocess.CompletedProcess:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(ROOT_DIR),
    )


def write_frame_list(tmp_path: Path, lines: list[str]) -> Path:
    frame_list = tmp_path / "frames.txt"
    frame_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return frame_list


# --- R-01: the clip never lands in the repository tree ---------------------


def test_output_inside_repo_tree_is_refused():
    with pytest.raises(SecurityError):
        verify_output_location(ROOT_DIR / "docs" / "demo.mp4")


def test_output_inside_a_repo_subdirectory_is_refused():
    # mlruns/ lives in the repo root by default with local MLflow tracking, so
    # "store it as a run artifact" has to mean a path outside the tree first.
    with pytest.raises(SecurityError):
        verify_output_location(ROOT_DIR / "mlruns" / "1" / "clip.mp4")


def test_output_outside_repo_tree_is_allowed(tmp_path):
    verify_output_location(tmp_path / "clip.mp4")


def test_non_mp4_output_is_refused():
    result = run_module(["--run-id", "a1", "--frame-list", "f.txt", "--output", "/tmp/clip.webm"])
    assert result.returncode == 1
    assert ".mp4" in result.stderr


# --- R-26: frames come only from the human-reviewed allowlist ---------------


def test_frame_outside_allowlist_is_refused(tmp_path):
    frame_list = write_frame_list(tmp_path, ["data/cholec/frame_1.png"])
    with pytest.raises(SecurityError):
        validate_and_resolve_frames(frame_list, {"demo-assets/ok/frame_1.png"})


def test_one_unauthorized_frame_fails_the_whole_render(tmp_path, monkeypatch):
    # No partial renders: an approved frame next to an unapproved one is still a refusal.
    # The approved frame has to exist on disk for this to reach the second entry, so the
    # repo root is redirected at a throwaway tree - validation walks the list in order and
    # a missing approved frame would otherwise mask the unapproved one behind it.
    import osv.demo.__main__ as demo

    approved = tmp_path / "demo-assets" / "ok" / "frame_1.png"
    approved.parent.mkdir(parents=True)
    approved.write_bytes(b"")
    monkeypatch.setattr(demo, "ROOT_DIR", tmp_path)

    frame_list = write_frame_list(
        tmp_path, ["demo-assets/ok/frame_1.png", "data/cholec/frame_2.png"]
    )
    with pytest.raises(SecurityError):
        demo.validate_and_resolve_frames(frame_list, {"demo-assets/ok/frame_1.png"})


def test_allowlisted_frame_missing_on_disk_is_an_error(tmp_path):
    frame_list = write_frame_list(tmp_path, ["demo-assets/ok/frame_1.png"])
    with pytest.raises(FileNotFoundError):
        validate_and_resolve_frames(frame_list, {"demo-assets/ok/frame_1.png"})


def test_empty_frame_list_is_refused(tmp_path):
    frame_list = write_frame_list(tmp_path, [])
    with pytest.raises(ValueError):
        validate_and_resolve_frames(frame_list, {"demo-assets/ok/frame_1.png"})


def test_render_is_refused_while_the_allowlist_is_empty(tmp_path):
    # Default-deny: the shipped allowlist has no frames, so nothing renders yet.
    frame_list = write_frame_list(tmp_path, ["demo-assets/ok/frame_1.png"])
    result = run_module(
        ["--run-id", "a1", "--frame-list", str(frame_list), "--output", str(tmp_path / "c.mp4")]
    )
    assert result.returncode == 1
    assert "allowlist" in result.stderr.lower()


# --- defects found in review, fixed and now pinned -------------------------


def test_load_allowlist_reads_the_shipped_file_format(tmp_path, monkeypatch):
    import osv.demo.__main__ as demo

    populated = tmp_path / "allowlist.yaml"
    populated.write_text(
        "frames:\n  - demo-assets/cholecseg8k/video01/frame_000123.png\n", encoding="utf-8"
    )
    monkeypatch.setattr(demo, "ALLOWLIST_PATH", populated)
    assert demo.load_allowlist() == {"demo-assets/cholecseg8k/video01/frame_000123.png"}


def test_hook_and_cli_agree_on_the_render_invocation(tmp_path):
    command = "python -m osv.demo " + " ".join(CANONICAL_ARGS)
    assert run_hook(command).returncode == 0, "demo_guard blocks the documented invocation"

    result = run_module(CANONICAL_ARGS)
    assert "unrecognized arguments" not in result.stderr
    assert "invalid choice" not in result.stderr


def test_hook_accepts_the_platform_temp_dir_the_module_accepts(tmp_path):
    out = (tmp_path / "clip.mp4").as_posix()
    verify_output_location(Path(out))  # module: allowed
    command = f'python -m osv.demo --run-id a1 --frame-list f.txt --output "{out}"'
    assert run_hook(command).returncode == 0


def test_hostile_run_id_is_refused(tmp_path):
    frame_list = write_frame_list(tmp_path, ["demo-assets/ok/frame_1.png"])
    result = run_module(
        [
            "--run-id", "a':fontsize=1:x=0'",
            "--frame-list", str(frame_list),
            "--output", str(tmp_path / "c.mp4"),
        ]
    )
    assert result.returncode != 0
    assert "run" in result.stderr.lower() and "id" in result.stderr.lower()


def test_frame_escaping_the_repo_tree_is_refused(tmp_path):
    escaping = "../../../etc/passwd.png"
    frame_list = write_frame_list(tmp_path, [escaping])
    with pytest.raises(SecurityError):
        validate_and_resolve_frames(frame_list, {escaping})


# --- the shipped allowlist itself ------------------------------------------


def test_shipped_allowlist_exists_and_is_currently_empty():
    # An empty allowlist is the intended default, not a bug: demo-recorder starts
    # producing clips the day a human clears the first frames.
    assert ALLOWLIST.exists()
    assert load_allowlist() == set()
