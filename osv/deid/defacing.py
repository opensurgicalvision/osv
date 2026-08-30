"""Layer 4: 3D defacing indicator check for volumetric scans.

Current implementation provides heuristic filename/marker inspection for
cranial CT/MRI scans. Full 3D geometric mesh / facial voxel surface analysis
(e.g., via `pydeface` / `mri_deface` integration) is scheduled for Phase 1 R3
when 3D volumetric datasets are onboarded.
"""


from __future__ import annotations

from pathlib import Path
from typing import Any

VOLUMETRIC_EXTENSIONS = (".nii", ".nii.gz", ".mha", ".mhd")


def inspect_3d_defacing(file_path: str | Path) -> list[dict[str, Any]]:
    """Inspect a 3D volumetric file (NIfTI / MetaImage) for defacing
    compliance."""
    path = Path(file_path)
    suffix = "".join(path.suffixes).lower()

    if not any(suffix.endswith(ext) for ext in VOLUMETRIC_EXTENSIONS):
        # 2D endoscopic images and non-volumetric files do not require 3D facial defacing
        return []

    violations: list[dict[str, Any]] = []

    # Check for defacing indicators or unmasked facial regions in cranial volumes
    # If filename indicates cranial/head scan without defacing flag:
    name_lower = path.name.lower()
    is_cranial = any(k in name_lower for k in ("head", "brain", "skull", "cranial", "face"))
    has_defaced_marker = any(k in name_lower for k in ("defaced", "deface", "anon", "stripped"))

    if is_cranial and not has_defaced_marker:
        violations.append(
            {
                "layer": "defacing",
                "code": "CRANIAL_VOLUME_UNVERIFIED_DEFACING",
                "message": f"Volumetric cranial file '{path.name}' lacks verified defacing marker.",
                "location": str(path),
            }
        )

    return violations
