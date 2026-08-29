#!/usr/bin/env python3
"""PreToolUse guard for Write|Edit|NotebookEdit.

Enforces R-01, R-02, R-04: raw medical data never reaches git, `data/raw/` is
never written from an agent session, and protected files are not edited without
an explicit human instruction naming them.

Contract: reads the hook payload as JSON on stdin. Exit 0 allows the call,
exit 2 blocks it and returns stderr to the model.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# R-01: medical payloads belong in DVC, never in git.
MEDICAL_SUFFIXES = {
    ".dcm", ".dicom", ".ima",
    ".nii", ".gz", ".mha", ".mhd", ".nrrd",
    ".mp4", ".avi", ".mov", ".mkv",
    ".svs", ".tiff",
}

# R-02: agent sessions never author anything inside these trees.
FORBIDDEN_DIRS = ("data/raw", "data/phi", "data/incoming")

# R-04: changing these needs a human who names the file in the prompt.
PROTECTED = (
    "LICENSE",
    "LICENSE-DATA",
    "LICENSE-DOCS",
    "docs/clinical-disclaimer.md",
    ".ai/context.md",
    ".ai/rules.md",
    ".github/workflows/",
    ".github/CODEOWNERS",
)


def rel(path_str: str) -> str:
    try:
        return Path(path_str).resolve().relative_to(Path.cwd().resolve()).as_posix()
    except (ValueError, OSError):
        return path_str.replace("\\", "/")


def block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)  # Never fail closed on a malformed payload; other layers still apply.

    tool_input = payload.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not target:
        sys.exit(0)

    posix = rel(target)
    lower = posix.lower()
    suffixes = {s.lower() for s in Path(posix).suffixes}

    if suffixes & MEDICAL_SUFFIXES and not lower.startswith("data/dvc"):
        block(
            f"BLOCKED by R-01: '{posix}' looks like raw medical data.\n"
            "Medical payloads are tracked with DVC, never written into the repo tree.\n"
            "Use `dvc add` on a path outside git, or write a loader script instead."
        )

    for forbidden in FORBIDDEN_DIRS:
        if lower.startswith(forbidden):
            block(
                f"BLOCKED by R-02: '{posix}' is inside '{forbidden}/'.\n"
                "Agent sessions never author files in the raw-data tree."
            )

    for protected in PROTECTED:
        if lower.startswith(protected.lower()):
            if os.environ.get("OSV_ALLOW_PROTECTED_EDIT") == posix:
                break
            block(
                f"BLOCKED by R-04: '{posix}' is a protected file.\n"
                "Licences, the clinical disclaimer, CI workflows and the canonical AI context\n"
                "change only through a human-authored PR that names the file explicitly."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
