#!/usr/bin/env python3
"""PostToolUse hook for user-facing documents.

Enforces R-03: model cards, dataset cards, READMEs and the served API surface
must carry the research-use disclaimer. Missing it is reported loudly rather
than silently patched, because the wording is legally reviewed and belongs to a
human (see R-04 on `docs/clinical-disclaimer.md`).

Contract: reads the hook payload as JSON on stdin. Exit 0 always; the warning is
surfaced to the model so it can fix the document in the same turn.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DISCLAIMER = "RESEARCH USE ONLY"

WATCHED_PARTS = (
    "docs/model-cards/",
    "docs/data-cards/",
    "osv/serve/",
)
WATCHED_NAMES = ("readme.md", "model_card.md", "model-card.md", "data_card.md", "data-card.md")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    target = (payload.get("tool_input") or {}).get("file_path", "")
    if not target:
        sys.exit(0)

    posix = target.replace("\\", "/").lower()
    watched = any(p in posix for p in WATCHED_PARTS) or Path(posix).name in WATCHED_NAMES
    if not watched:
        sys.exit(0)

    path = Path(target)
    if not path.exists():
        sys.exit(0)

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        sys.exit(0)

    if DISCLAIMER not in content.upper():
        print(
            f"disclaimer_guard (R-03): '{target}' is user-facing but has no "
            f"'{DISCLAIMER} - NOT FOR CLINICAL USE' notice.\n"
            "Add it near the top, copying the exact wording from docs/clinical-disclaimer.md.\n"
            "Do not paraphrase: the wording is legally reviewed.",
            file=sys.stderr,
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
