"""Test that the demo_guard hook holds R-26 in both directions.

A guard is only worth its refusals if the allowed calls still go through: a hook
that blocks too much gets disabled by the first tired volunteer, and a disabled
hook protects nothing (see the reliability note in plan Sec. 5.7). So this
covers the blocks and the passes with the same weight.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
HOOK = ROOT_DIR / ".ai" / "hooks" / "demo_guard.py"

ALLOWED = 0
BLOCKED = 2


def run_hook(payload) -> subprocess.CompletedProcess:
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=data,
        capture_output=True,
        text=True,
        cwd=str(ROOT_DIR),
    )


def bash(command: str):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def write(path: str, tool: str = "Write"):
    return {"tool_name": tool, "tool_input": {"file_path": path}}


# --- calls that must still work -------------------------------------------


def test_ordinary_bash_passes():
    assert run_hook(bash("git status")).returncode == ALLOWED


def test_installing_an_ffmpeg_dependency_passes():
    # Matched on the executable name, not as a substring: blocking `pip install
    # imageio-ffmpeg` would teach people to work around the guard.
    assert run_hook(bash("pip install imageio-ffmpeg")).returncode == ALLOWED


def test_sanctioned_render_passes(tmp_path):
    # The canonical invocation: run id, a frame list, and an output path outside the tree.
    out = (Path(tempfile.gettempdir()) / "clip.mp4").as_posix()
    frame_list = tmp_path / "frames.txt"
    frame_list.write_text("", encoding="utf-8")
    cmd = f'python -m osv.demo --run-id a1 --frame-list "{frame_list.as_posix()}" --output "{out}"'
    assert run_hook(bash(cmd)).returncode == ALLOWED


def test_writing_an_experiment_card_passes():
    assert run_hook(write("docs/arch-experiments/e-001.md")).returncode == ALLOWED


def test_merely_naming_the_renderer_is_not_invoking_it():
    # Regression: the first version matched "osv.demo" anywhere in the command, so a
    # script whose comment mentioned the module was refused as an unsafe render.
    assert run_hook(bash("grep -rn 'osv.demo' docs/")).returncode == ALLOWED
    assert run_hook(bash("echo '# osv.demo renders the clip' >> notes.txt")).returncode == ALLOWED


def test_merely_naming_a_publish_command_is_not_publishing():
    # Same class: the words in a heredoc or a commit message are not an upload.
    assert run_hook(bash("git commit -m 'document the hf upload boundary'")).returncode == ALLOWED


def test_malformed_payload_does_not_fail_closed():
    # A hook that breaks the session on its own error is the one that gets removed.
    assert run_hook("not json").returncode == ALLOWED


# --- R-26 refusals ---------------------------------------------------------


def test_raw_ffmpeg_render_is_blocked():
    result = run_hook(bash("ffmpeg -i frames/%04d.png out.mp4"))
    assert result.returncode == BLOCKED
    assert "osv.demo" in result.stderr


def test_publishing_outward_is_blocked():
    assert run_hook(bash("hf upload osv/demo clip.mp4")).returncode == BLOCKED
    assert run_hook(bash("glab release upload v0.2.0 clip.mp4")).returncode == BLOCKED


def test_render_without_run_id_is_blocked():
    cmd = "python -m osv.demo --frame-list f.txt --output /tmp/clip.mp4"
    assert run_hook(bash(cmd)).returncode == BLOCKED


def test_render_without_frame_list_is_blocked():
    # Frames reach the renderer only through --frame-list; there is no other input path.
    cmd = "python -m osv.demo --run-id a1 --output /tmp/clip.mp4"
    result = run_hook(bash(cmd))
    assert result.returncode == BLOCKED
    assert "--frame-list" in result.stderr


def test_frame_outside_allowlist_is_blocked():
    cmd = (
        "python -m osv.demo --run-id a1 --frame-list f.txt "
        "--frame data/cholec/frame_1.png --output /tmp/clip.mp4"
    )
    result = run_hook(bash(cmd))
    assert result.returncode == BLOCKED
    assert "allowlist" in result.stderr


def test_unauthorized_frame_inside_the_frame_list_file_is_blocked(tmp_path):
    # The real invocation passes frames in a file, so the guard has to open it.
    frame_list = tmp_path / "frames.txt"
    frame_list.write_text("data/cholec/frame_1.png\n", encoding="utf-8")
    out = (Path(tempfile.gettempdir()) / "clip.mp4").as_posix()
    cmd = f'python -m osv.demo --run-id a1 --frame-list "{frame_list.as_posix()}" --output "{out}"'
    result = run_hook(bash(cmd))
    assert result.returncode == BLOCKED
    assert "allowlist" in result.stderr


def test_clip_written_into_repo_tree_is_blocked():
    cmd = "python -m osv.demo --run-id a1 --frame-list f.txt --output docs/demo.mp4"
    assert run_hook(bash(cmd)).returncode == BLOCKED


def test_clip_written_into_mlruns_inside_the_checkout_is_blocked():
    # mlruns/ is in the repo root under local MLflow tracking, so it is the repo tree.
    cmd = "python -m osv.demo --run-id a1 --frame-list f.txt --output mlruns/1/clip.mp4"
    assert run_hook(bash(cmd)).returncode == BLOCKED


def test_editing_the_allowlist_is_blocked():
    # The allowlist is the trust anchor: a frame is added by a human who checked
    # its licence and its OCR result, never by the agent that wants to use it.
    assert run_hook(write("demo-assets/allowlist.yaml", tool="Edit")).returncode == BLOCKED


def test_writing_a_video_into_the_tree_is_blocked():
    assert run_hook(write("docs/clip.mp4")).returncode == BLOCKED
