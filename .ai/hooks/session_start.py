#!/usr/bin/env python3
"""SessionStart hook: put the non-negotiables in front of the model every session.

The red lines are in the context file, but a session that starts mid-task can
drift. This restates the five things whose violation is irreversible, plus the
live state of the repo, and costs a few hundred tokens.

Contract: stdout is injected into the session as context. Always exits 0.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10, cwd=ROOT, check=False
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def dvc_state() -> str:
    lock = ROOT / "dvc.lock"
    if not lock.exists():
        return "no dvc.lock yet"
    try:
        import hashlib

        digest = hashlib.sha256(lock.read_bytes()).hexdigest()[:12]
        return f"dvc.lock {digest}"
    except OSError:
        return "dvc.lock unreadable"


def main() -> None:
    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    dirty = "dirty" if git("status", "--porcelain") else "clean"

    print("## OSV session context\n")
    print(f"- Branch `{branch}` ({dirty}) | {dvc_state()}")
    print("- Full rules: `.ai/rules.md` | Canonical context: `.ai/context.md`\n")
    print("**Irreversible if violated - check before acting:**")
    print("1. R-01/R-02 No raw medical data into git. DVC only, never `data/raw/`.")
    print("2. R-03 Every user-facing artefact says `RESEARCH USE ONLY - NOT FOR CLINICAL USE`.")
    print("3. R-05 Notebook outputs are PHI. They get stripped, never committed.")
    print("4. R-08 Splits are by patient, never by frame.")
    print("5. R-14 Anatomy, boundaries and any clinical claim belong to the Clinical Lead, not to you.\n")
    print("Edit `.ai/`, never `.claude/` - generated files are checked in CI (R-13).")

    sys.exit(0)


if __name__ == "__main__":
    main()
