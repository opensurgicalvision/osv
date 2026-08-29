#!/usr/bin/env python3
"""PostToolUse hook: format and lint touched Python files.

Keeps style out of code review entirely, so reviewers spend their four hours a
week on correctness instead of import order.

Contract: reads the hook payload as JSON on stdin. Always exits 0 — a missing
`ruff` must not stall a session.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    target = (payload.get("tool_input") or {}).get("file_path", "")
    if not target.endswith(".py") or not Path(target).exists():
        sys.exit(0)

    ruff = shutil.which("ruff")
    if not ruff:
        sys.exit(0)

    for args in (["format", target], ["check", "--fix", "--quiet", target]):
        try:
            subprocess.run([ruff, *args], capture_output=True, timeout=30, check=False)
        except (subprocess.SubprocessError, OSError):
            break

    try:
        result = subprocess.run(
            [ruff, "check", "--quiet", target], capture_output=True, text=True, timeout=30, check=False
        )
    except (subprocess.SubprocessError, OSError):
        sys.exit(0)

    if result.returncode != 0 and result.stdout.strip():
        print(f"ruff still reports issues in {target}:\n{result.stdout.strip()[:1500]}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
