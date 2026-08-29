#!/usr/bin/env python3
"""PostToolUse hook for notebooks.

Enforces R-05. A rendered surgical frame sitting in an `.ipynb` output cell is
patient data committed to a public repository in a form no DICOM tag scrubber
will ever look at. This is the single most common way medical projects leak
imagery, so outputs are stripped on every write rather than at review time.

Contract: reads the hook payload as JSON on stdin. Always exits 0 — this hook
repairs, it does not block.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    target = tool_input.get("notebook_path") or tool_input.get("file_path") or ""
    if not target.endswith(".ipynb"):
        sys.exit(0)

    path = Path(target)
    if not path.exists():
        sys.exit(0)

    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        print(f"notebook_guard: could not parse {target}; strip outputs manually.", file=sys.stderr)
        sys.exit(0)

    stripped = 0
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("outputs"):
            stripped += len(cell["outputs"])
            cell["outputs"] = []
        if cell.get("execution_count") is not None:
            cell["execution_count"] = None

    if stripped:
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            f"notebook_guard (R-05): stripped {stripped} output(s) from {target}. "
            "Rendered frames in notebook outputs count as PHI.",
            file=sys.stderr,
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
