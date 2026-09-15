#!/usr/bin/env python3
"""PreToolUse guard for demo clip rendering (Write|Edit|NotebookEdit and Bash).

Enforces R-26 and the demo half of R-01/R-03: a clip is rendered only from
frames listed in `demo-assets/allowlist.yaml`, carries a burned-in run id and
disclaimer, lands in tracker artifacts rather than the git tree, and is never
published outward from an agent session.

Why a hook and not an instruction in the agent file: a demo clip is by
definition made to be shown, which makes it the shortest path from the
repository to the public. A frame whose licence forbids redistribution, or one
with burned-in patient text, is unrecoverable once it is out. `demo-recorder`
states these boundaries; this hook is what makes them hold when the agent is
told otherwise.

Contract: reads the hook payload as JSON on stdin. Exit 0 allows the call,
exit 2 blocks it and returns stderr to the model.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

ALLOWLIST_FILE = Path("demo-assets/allowlist.yaml")

VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".gif"}
FRAME_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}

# The one sanctioned renderer. Everything else that can mux frames into a video
# is refused here rather than validated: allowlist checking, the burned-in
# disclaimer and the run id live inside `osv.demo`, so a raw ffmpeg pipeline is
# not a shortcut, it is the same job with all the guarantees removed.
SANCTIONED_RENDERER = {"osv.demo", "osv_demo", "osv-demo"}
# Matched on the executable name, not as a substring: `pip install imageio-ffmpeg`
# installs a dependency, it does not render anything, and blocking it would teach
# people to work around the guard rather than through it.
UNSANCTIONED_RENDERERS = {"ffmpeg", "ffmpeg.exe", "avconv", "avconv.exe"}

# Publishing outward is a human action (Sec. 6.3). These never run from an agent session.
PUBLISH_PATTERNS = (
    "hf upload",
    "huggingface-cli upload",
    "gh release upload",
    "youtube-upload",
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def inside_repo(path_str: str) -> bool:
    """True when the path resolves to somewhere inside the repository tree.

    The same predicate `osv.demo` applies to its own output. A prefix list
    (`mlruns/`, `/tmp/`) was the obvious shortcut and the wrong one: it says yes to
    `mlruns/`, which lives in the repo root under local MLflow tracking, and no to the
    platform temp directory on Windows - where half this team works.
    """
    try:
        (REPO_ROOT / path_str).resolve().relative_to(REPO_ROOT)
        return True
    except (ValueError, OSError):
        return False


def block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def load_allowlist() -> set[str] | None:
    """Frames declared in demo-assets/allowlist.yaml, as posix paths.

    Deliberately a line scan rather than a yaml dependency, for the same reason
    build.py parses agent frontmatter by hand: one shape of one file does not
    justify a package that then has to exist in every hook environment.
    Returns None when the file is missing.
    """
    if not ALLOWLIST_FILE.exists():
        return None
    frames: set[str] = set()
    in_frames = False
    for raw in ALLOWLIST_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith((" ", "\t", "-")):
            in_frames = line.strip().startswith("frames:")
            # `frames: []` on one line is an explicit empty allowlist.
            continue
        if in_frames and line.strip().startswith("- "):
            frames.add(line.strip()[2:].strip().strip("\"'").replace("\\", "/"))
    return frames


def path_tokens(command: str) -> list[str]:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = re.split(r"\s+", command)
    out = []
    for token in tokens:
        cleaned = token.lstrip("@").strip("\"'")
        if "=" in cleaned and not cleaned.startswith("-"):
            cleaned = cleaned.split("=", 1)[1]
        if "/" in cleaned or "\\" in cleaned or "." in cleaned:
            out.append(cleaned.replace("\\", "/"))
    return out


def tokenize(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return re.split(r"\s+", command)


def invokes(tokens: list[str], executables: set[str]) -> bool:
    """True when one of `executables` is actually invoked, by basename."""
    for token in tokens:
        base = token.strip("\"'").replace("\\", "/").rsplit("/", 1)[-1].lower()
        if base in executables:
            return True
    return False


def invokes_renderer(tokens: list[str]) -> bool:
    """True for `python -m osv.demo ...` or an `osv-demo` executable.

    Deliberately not a substring test on the whole command. The first version was, and
    it blocked a shell script whose *comment* mentioned osv.demo: naming the renderer is
    not invoking it, and a guard that cannot tell the difference gets switched off.
    """
    for index, token in enumerate(tokens):
        bare = token.strip("\"'")
        if bare in SANCTIONED_RENDERER and index > 0 and tokens[index - 1] == "-m":
            return True
        if bare.replace("\\", "/").rsplit("/", 1)[-1].lower() in {"osv-demo", "osv-demo.exe"}:
            return True
    return False


def publishes_outward(tokens: list[str]) -> str | None:
    """The publish command being invoked, if any -- matched on adjacent tokens.

    Same reason as invokes_renderer: a heredoc or a commit message that contains the
    words "hf upload" is not a publish.
    """
    cleaned = [token.strip("\"'").lower() for token in tokens]
    widths = {len(pattern.split()) for pattern in PUBLISH_PATTERNS}
    for width in sorted(widths):
        for start in range(len(cleaned) - width + 1):
            candidate = " ".join(cleaned[start : start + width])
            if candidate in PUBLISH_PATTERNS:
                return candidate
    return None


def check_bash(command: str) -> None:
    tokens = tokenize(command)

    published = publishes_outward(tokens)
    if published:
        block(
            f"BLOCKED by R-26: '{published}' publishes outward.\n"
            "A demo clip leaves the project only through a human (R7/R6), taken from the\n"
            "finished tracker artifact. Link the artifact in the PR instead."
        )

    is_sanctioned = invokes_renderer(tokens)
    is_unsanctioned = invokes(tokens, UNSANCTIONED_RENDERERS)

    if is_unsanctioned and not is_sanctioned:
        block(
            "BLOCKED by R-26: direct video muxing bypasses the demo contract.\n"
            "Render through `python -m osv.demo --run-id <id> --disclaimer`, which enforces the\n"
            "frame allowlist and burns in the run id and RESEARCH USE ONLY notice."
        )

    if not is_sanctioned:
        return

    check_sanctioned_render(command)


def check_sanctioned_render(command: str) -> None:
    """Validate a `python -m osv.demo` invocation once `check_bash` has confirmed it is one:
    the run id and frame-list flags are present, the allowlist exists, and every frame or
    output path named on the command line clears R-26. Split out of `check_bash` so each
    function stays readable on its own rather than for any behavioral reason."""
    if "--run-id" not in command:
        block("BLOCKED by R-26: a demo clip must carry `--run-id` so it traces back to its run.")
    if "--frame-list" not in command:
        block(
            "BLOCKED by R-26: frames are passed as `--frame-list <file>`, one allowlisted path\n"
            "per line. There is no other way to hand frames to the renderer.\n"
            "The RESEARCH USE ONLY notice needs no flag - osv.demo burns it in unconditionally."
        )

    allowlist = load_allowlist()
    if allowlist is None:
        block(
            f"BLOCKED by R-26: '{ALLOWLIST_FILE.as_posix()}' is missing.\n"
            "Frames for a demo are licence-checked and OCR-scanned by a human before they can be\n"
            "shown. No allowlist means nothing is renderable yet - that is the intended default."
        )

    for token in path_tokens(command):
        suffix = Path(token).suffix.lower()
        normalized = token[2:] if token.startswith("./") else token
        if suffix in FRAME_SUFFIXES:
            check_frame(normalized, allowlist)
        elif suffix in VIDEO_SUFFIXES:
            if inside_repo(normalized):
                block(
                    f"BLOCKED by R-01/R-26: clip output '{normalized}' is inside the repo tree.\n"
                    "Render to a path outside the repository, then attach it as a run artifact.\n"
                    "The PR carries a markdown link, never the video."
                )
        elif suffix == ".txt":
            check_frame_list_file(normalized, allowlist)


def check_frame(frame: str, allowlist: set[str]) -> None:
    if frame not in allowlist:
        block(
            f"BLOCKED by R-26: frame '{frame}' is not in {ALLOWLIST_FILE.as_posix()}.\n"
            "Only frames whose licence permits redistribution and which passed the\n"
            "burned-in-text OCR scan may appear in a clip. Adding one is a human PR."
        )


def check_frame_list_file(path_str: str, allowlist: set[str]) -> None:
    """Check every entry of a `--frame-list` file that is already on disk.

    Frames reach the renderer through this file rather than through argv, so without
    reading it the allowlist check above never sees a real invocation. `osv.demo`
    validates the same list again - this is the layer that refuses before the process
    starts. A file that cannot be read is left alone: the renderer will refuse it, and a
    hook that guesses about missing inputs blocks legitimate work.
    """
    candidate = Path(path_str)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    try:
        lines = candidate.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    for line in lines:
        entry = line.strip().replace("\\", "/")
        if entry and Path(entry).suffix.lower() in FRAME_SUFFIXES:
            check_frame(entry, allowlist)


def check_write(target: str) -> None:
    posix = target.replace("\\", "/")
    lowered = posix.lower()

    if lowered.endswith("demo-assets/allowlist.yaml"):
        block(
            "BLOCKED by R-26: the demo frame allowlist is not edited from an agent session.\n"
            "It is the trust anchor of the whole mechanism - a frame is added by a human who\n"
            "checked its licence and its OCR result."
        )

    if Path(lowered).suffix in VIDEO_SUFFIXES:
        block(
            f"BLOCKED by R-01/R-26: '{posix}' is a video file inside the repo tree.\n"
            "Clips are tracker artifacts and release assets; the PR carries a link to one."
        )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)  # Never fail closed on a malformed payload; other layers still apply.

    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}

    if tool_name == "Bash":
        command = tool_input.get("command") or ""
        if command:
            check_bash(command)
    else:
        target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if target:
            check_write(target)

    sys.exit(0)


if __name__ == "__main__":
    main()
