import argparse
import re
import sys
import tempfile
import subprocess
import os
from pathlib import Path
import yaml

# Hardcoded constraints for medical integrity and project rules
DISCLAIMER_TEXT = "RESEARCH USE ONLY - NOT FOR CLINICAL USE"
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ALLOWLIST_PATH = ROOT_DIR / "demo-assets" / "allowlist.yaml"

# A run id is burned into the frame through the ffmpeg -vf filtergraph. A quote in it
# closes `text=` and everything after is parsed as filter options, which is enough to
# shrink the disclaimer to one pixel or push it off-screen -- an unremovable watermark
# that the caller can remove. The run id comes from an agent, and agents read untrusted
# MR content, so the charset is restricted instead of escaped.
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,64}")


class SecurityError(Exception):
    """Raised when a project security constraint (like R-01, R-26) is violated."""
    pass


def is_inside_repo(path: Path) -> bool:
    """True when `path` resolves to somewhere inside the repository tree."""
    try:
        path.resolve().relative_to(ROOT_DIR.resolve())
        return True
    except ValueError:
        return False


def validate_run_id(run_id: str) -> str:
    """Reject any run id that could alter the filtergraph it is interpolated into."""
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise SecurityError(
            f"SECURITY BLOCK (R-26): run id '{run_id}' contains characters that are not "
            "allowed. A run id is burned into the video through the ffmpeg filtergraph, so it "
            "is restricted to letters, digits, dot, underscore and hyphen (max 64 chars)."
        )
    return run_id


def load_allowlist() -> set[str]:
    """Load the pre-approved frame allowlist. Fail closed if missing/empty/malformed.

    The file is a mapping with a `frames:` list, the same shape the demo_guard hook
    parses -- the two layers have to agree on the format or the render path is dead in
    a way that looks exactly like the intended default-deny.
    """
    if not ALLOWLIST_PATH.exists():
        return set()

    try:
        data = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"[osv.demo] WARNING: {ALLOWLIST_PATH} is not valid YAML: {exc}", file=sys.stderr)
        return set()

    if not isinstance(data, dict):
        print(
            f"[osv.demo] WARNING: {ALLOWLIST_PATH} has no top-level `frames:` mapping.",
            file=sys.stderr,
        )
        return set()

    frames = data.get("frames") or []
    if not isinstance(frames, list):
        print(f"[osv.demo] WARNING: `frames:` in {ALLOWLIST_PATH} is not a list.", file=sys.stderr)
        return set()

    return {str(f).strip().replace("\\", "/") for f in frames if str(f).strip()}


def validate_and_resolve_frames(frame_list_file: Path, allowlist: set[str]) -> list[Path]:
    """Read a list of relative frame paths and validate every single one against the allowlist."""
    with open(frame_list_file, "r", encoding="utf-8") as f:
        # Read lines, strip whitespace, ignore empty lines
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        raise ValueError("Provided frame list file is empty.")

    validated_paths = []
    for line in lines:
        # Normalize the relative path for strictly exact matching against allowlist
        rel_path = Path(line).as_posix()

        if rel_path not in allowlist:
            raise SecurityError(
                f"SECURITY BLOCK: Frame '{rel_path}' is not explicitly permitted in "
                "demo-assets/allowlist.yaml"
            )

        full_path = (ROOT_DIR / rel_path).resolve()

        # An approved entry that is a symlink, or contains '..', resolves somewhere the
        # human who approved it never looked at. The allowlist authorises a frame, not a
        # path shape, so containment is checked separately.
        if not is_inside_repo(full_path):
            raise SecurityError(
                f"SECURITY BLOCK (R-26): Frame '{rel_path}' resolves to {full_path}, outside "
                "the repository tree. An allowlisted frame is a file in this repository, not a "
                "link to one somewhere else."
            )

        if not full_path.exists():
            raise FileNotFoundError(f"Frame file not found on disk: {full_path}")

        validated_paths.append(full_path)

    return validated_paths


def verify_output_location(output_path: Path):
    """Enforce R-01: No .mp4 files inside the git repository tree."""
    if is_inside_repo(output_path):
        raise SecurityError(
            f"SECURITY BLOCK (R-01): Cannot write .mp4 to {output_path}.\n"
            "Demo clips must be written outside the repository tree (e.g., the platform temp "
            "directory), then attached as a run artifact from there."
        )


def render_clip(
    run_id: str, frames: list[Path], output_path: Path, fps: int = 10, font: str | None = None
):
    """Render the validated frames using ffmpeg with burned-in text."""
    # Create a temporary concat demuxer file for ffmpeg
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as concat_file:
        for frame in frames:
            concat_file.write(f"file '{frame.resolve().as_posix()}'\n")
            concat_file.write(f"duration {1.0 / fps}\n")
        # Repeat the last frame without duration to avoid dropping it
        concat_file.write(f"file '{frames[-1].resolve().as_posix()}'\n")
        concat_path = concat_file.name

    # Build the drawtext filters for the watermarks. run_id passed validate_run_id, so it
    # carries nothing that needs escaping inside the filtergraph - and the label avoids a
    # colon of its own, which would otherwise need escaping at two levels.
    font_opt = f"fontfile='{font}':" if font else ""

    # Disclaimer at the bottom center
    drawtext_disclaimer = (
        f"drawtext={font_opt}text='{DISCLAIMER_TEXT}':"
        "x=(w-text_w)/2:y=h-th-20:"
        "fontsize=24:fontcolor=white:box=1:boxcolor=black@0.7"
    )
    # Run ID at the top left
    drawtext_run = (
        f"drawtext={font_opt}text='Run {run_id}':"
        "x=20:y=20:"
        "fontsize=20:fontcolor=white:box=1:boxcolor=black@0.7"
    )

    vf_string = f"{drawtext_disclaimer},{drawtext_run}"

    cmd = [
        "ffmpeg",
        "-y",               # Overwrite existing
        "-f", "concat",     # Use concat demuxer
        "-safe", "0",       # Required for absolute paths in concat file
        "-i", concat_path,
        "-vf", vf_string,   # Video filters (watermarks)
        "-c:v", "libx264",  # H.264 codec
        "-pix_fmt", "yuv420p", # Broad compatibility
        "-r", str(fps),     # Constant output rate: concat durations alone give a VFR stream
        output_path.as_posix()
    ]

    print(f"[osv.demo] Rendering {len(frames)} frames to {output_path}...")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"[osv.demo] SUCCESS. Clip rendered at {output_path}")
    except FileNotFoundError:
        print(
            "[osv.demo] ERROR: ffmpeg is not on PATH. It is the only renderer this module "
            "shells out to; install it or run inside the project container.",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("[osv.demo] FFMPEG ERROR:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        if "Cannot find a valid font" in (e.stderr or ""):
            print(
                "[osv.demo] HINT: drawtext could not resolve a font. Pass --font "
                "<path-to-ttf>; the watermark is not optional, so the render fails instead.",
                file=sys.stderr,
            )
        sys.exit(1)
    finally:
        os.remove(concat_path)


def main():
    parser = argparse.ArgumentParser(
        description="Secure deterministic demo clip renderer (R-26)",
        prog="python -m osv.demo"
    )
    parser.add_argument("--run-id", required=True, help="MLflow/W&B Run ID to burn into the video")
    parser.add_argument(
        "--frame-list",
        required=True,
        type=Path,
        help="Text file with one relative frame path per line",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output .mp4 path (must be outside repo tree)",
    )
    parser.add_argument("--fps", type=int, default=10, help="Framerate (default: 10)")
    parser.add_argument(
        "--font",
        default=None,
        help="Path to a .ttf for the burned-in text. Needed where fontconfig cannot resolve a "
        "default family (typically Windows).",
    )

    args = parser.parse_args()

    if args.output.suffix.lower() != ".mp4":
        print("[osv.demo] ERROR: Output file must have .mp4 extension.", file=sys.stderr)
        sys.exit(1)

    try:
        # 1. Enforce R-01 (No MP4 in git)
        verify_output_location(args.output)

        # 2. Reject a run id that could rewrite the watermark filtergraph
        run_id = validate_run_id(args.run_id)

        # 3. Fail closed if allowlist missing/empty
        allowlist = load_allowlist()
        if not allowlist:
            print("[osv.demo] SECURITY BLOCK: demo-assets/allowlist.yaml is missing or empty. "
                  "No frames are authorized for rendering.", file=sys.stderr)
            sys.exit(1)

        # 4. Validate every frame explicitly
        valid_frames = validate_and_resolve_frames(args.frame_list, allowlist)

        # 5. Render
        render_clip(run_id, valid_frames, args.output, args.fps, args.font)

    except SecurityError as e:
        print(f"\n{e}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[osv.demo] UNEXPECTED ERROR: {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
