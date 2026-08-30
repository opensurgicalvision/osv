"""CLI entry point for the deterministic de-identification gate.

This is Stage A of the deid-gate agent's two-piece design (see
.ai/agents/deid-gate.md): it runs on a plain CI pipeline with no LLM secret, so
it executes with zero prompt-injection risk, and its verdict is what `deid-gate`
(the LLM agent, Stage B) later reads and explains -- never recomputes.

Deterministic verification layers:
  * Layer 1: PS3.15 Annex E standard tag validation (DICOM).
  * Layer 2: Private vendor tag scanning and stripping (odd groups).
  * Layer 3: Morphological edge + OCR text candidate detection in pixel space.
  * Layer 4: Volumetric defacing indicator check (cranial CT/MRI).
"""


from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from osv.deid import verify_no_phi

LAYER_NAMES = ("ps3_15_tags", "private_tags", "burned_in_ocr", "defacing")


def scan_files(file_paths: list[str]) -> dict[str, Any]:
    """Run verify_no_phi over each file and aggregate into the schema
    deid-gate.md documents reading from deid-verdict.json."""
    per_file: list[dict[str, Any]] = []
    all_violations: list[dict[str, Any]] = []

    for file_path in file_paths:
        result = verify_no_phi(file_path)
        per_file.append(result)
        for violation in result.get("violations", []):
            all_violations.append({"file": file_path, **violation})

    overall = "pass" if not all_violations else "fail"

    layers: dict[str, list[dict[str, Any]]] = {name: [] for name in LAYER_NAMES}
    for violation in all_violations:
        layer = violation.get("layer", "ps3_15_tags")
        layers.setdefault(layer, []).append(violation)

    return {
        "overall": overall,
        "files_scanned": file_paths,
        "layers": layers,
        "violations_total": len(all_violations),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic 4-layer de-identification scan.")
    parser.add_argument("paths", nargs="+", help="Files to scan (e.g. from `git diff --name-only`).")
    parser.add_argument(
        "--out",
        default="deid-verdict.json",
        help="Where to write the verdict JSON (default: deid-verdict.json in the cwd).",
    )
    args = parser.parse_args(argv)

    verdict = scan_files(args.paths)

    out_path = Path(args.out)
    out_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")

    print(f"deid-scan: {verdict['overall'].upper()} ({verdict['violations_total']} violation(s)) -> {out_path}")

    return 0 if verdict["overall"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
