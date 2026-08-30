"""4-layer De-identification and PHI defense framework.

Layer 1: PS3.15 standard DICOM tag scrubbing
Layer 2: Private vendor tag removal (odd groups)
Layer 3: OCR inspection for burned-in pixel text annotations
Layer 4: 3D defacing for cranial CT/MRI scans
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from osv.deid.defacing import inspect_3d_defacing
from osv.deid.dicom import inspect_dicom_tags
from osv.deid.ocr import inspect_burned_in_text

DICOM_EXTENSIONS = {".dcm", ".ima"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
VOLUMETRIC_EXTENSIONS = {".nii", ".nii.gz", ".mha", ".mhd"}


def verify_no_phi(file_path: str | Path) -> dict[str, Any]:
    """Inspects a file or dataset sample for PHI, unauthorized tags, or
    burned-in annotations across all 4 defense layers."""
    path = Path(file_path)
    if not path.exists():
        return {
            "file_path": str(file_path),
            "clean": False,
            "violations": [
                {
                    "layer": "ps3_15_tags",
                    "code": "FILE_NOT_FOUND",
                    "message": f"Target file does not exist: {file_path}",
                    "location": str(file_path),
                }
            ],
        }

    violations: list[dict[str, Any]] = []
    suffix = path.suffix.lower()
    full_suffixes = "".join(path.suffixes).lower()

    # 1 & 2. DICOM tag inspections
    if suffix in DICOM_EXTENSIONS:
        violations.extend(inspect_dicom_tags(path))

    # 3. OCR burned-in pixel inspections for images
    if suffix in IMAGE_EXTENSIONS:
        violations.extend(inspect_burned_in_text(path))

    # 4. Volumetric defacing inspections
    if any(full_suffixes.endswith(ext) for ext in VOLUMETRIC_EXTENSIONS):
        violations.extend(inspect_3d_defacing(path))

    return {
        "file_path": str(file_path),
        "clean": len(violations) == 0,
        "violations": violations,
    }


__all__ = [
    "verify_no_phi",
    "inspect_dicom_tags",
    "inspect_burned_in_text",
    "inspect_3d_defacing",
]
