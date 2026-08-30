"""DICOM tag inspection and de-identification verification.

Layer 1: PS3.15 standard DICOM tag scrubbing.
Layer 2: Private vendor tag removal (odd groups).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pydicom
    from pydicom.dataset import Dataset
    from pydicom.tag import Tag
except ImportError:
    pydicom = None  # type: ignore[assignment]
    Dataset = None  # type: ignore[assignment,misc]
    Tag = None  # type: ignore[assignment,misc]

# Core identifying DICOM tags per PS3.15 Basic Application Level Confidentiality Profile (Annex E)
PS3_15_TAGS_TO_CHECK: tuple[tuple[int, int, str], ...] = (
    (0x0010, 0x0010, "PatientName"),
    (0x0010, 0x0020, "PatientID"),
    (0x0010, 0x0030, "PatientBirthDate"),
    (0x0010, 0x0032, "PatientBirthTime"),
    (0x0010, 0x0040, "PatientSex"),
    (0x0010, 0x1000, "OtherPatientIDs"),
    (0x0010, 0x1001, "OtherPatientNames"),
    (0x0010, 0x1010, "PatientAge"),
    (0x0010, 0x1040, "PatientAddress"),
    (0x0010, 0x2154, "PatientTelephoneNumbers"),
    (0x0010, 0x4000, "PatientComments"),
    (0x0008, 0x0020, "StudyDate"),
    (0x0008, 0x0021, "SeriesDate"),
    (0x0008, 0x0022, "AcquisitionDate"),
    (0x0008, 0x0023, "ContentDate"),
    (0x0008, 0x0030, "StudyTime"),
    (0x0008, 0x0031, "SeriesTime"),
    (0x0008, 0x0032, "AcquisitionTime"),
    (0x0008, 0x0033, "ContentTime"),
    (0x0008, 0x0050, "AccessionNumber"),
    (0x0008, 0x0080, "InstitutionName"),
    (0x0008, 0x0081, "InstitutionAddress"),
    (0x0008, 0x0090, "ReferringPhysicianName"),
    (0x0008, 0x0092, "ReferringPhysicianAddress"),
    (0x0008, 0x0094, "ReferringPhysicianTelephoneNumbers"),
    (0x0008, 0x1040, "InstitutionalDepartmentName"),
    (0x0008, 0x1048, "PhysiciansOfRecord"),
    (0x0008, 0x1050, "PerformingPhysicianName"),
    (0x0008, 0x1060, "NameOfPhysiciansReadingStudy"),
    (0x0008, 0x1070, "OperatorsName"),
    (0x0008, 0x1090, "ManufacturerModelName"),
    (0x0018, 0x1000, "DeviceSerialNumber"),
    (0x0020, 0x0010, "StudyID"),
)

# Allowlist for vetted non-identifying private tags (if any)
PRIVATE_TAG_ALLOWLIST: set[tuple[int, int]] = set()

# Standard safe placeholder values commonly placed by de-identification tools
SAFE_ANONYMIZED_VALUES: set[str] = {
    "",
    "ANONYMOUS",
    "ANONYMIZED",
    "ANON",
    "REMOVED",
    "DEIDENTIFIED",
    "RESEARCH_ONLY",
    "NONE",
    "UNKNOWN",
    "EMPTY",
}

SAFE_ANONYMIZED_PREFIXES: tuple[str, ...] = (
    "ANON",
    "ANONYMOUS",
    "PATIENT_",
    "SUB-",
    "SUB_",
    "SUBJECT_",
    "CASE_",
    "CHOL_",
    "OSV_",
)


def is_value_identifying(val: Any) -> bool:
    """Determine if a tag value contains potentially identifying data."""
    if val is None:
        return False
    str_val = str(val).strip()
    if not str_val:
        return False
    val_upper = str_val.upper()
    if val_upper in SAFE_ANONYMIZED_VALUES:
        return False
    if any(val_upper.startswith(prefix) for prefix in SAFE_ANONYMIZED_PREFIXES):
        return False
    return True



def inspect_dicom_tags(file_path: str | Path) -> list[dict[str, Any]]:
    """Inspect a DICOM file for PS3.15 violations (Layer 1) and unvetted
    private tags (Layer 2)."""
    if pydicom is None:
        return [
            {
                "layer": "ps3_15_tags",
                "code": "MISSING_DEPENDENCY",
                "message": "pydicom is required to inspect DICOM files.",
                "location": str(file_path),
            }
        ]

    violations: list[dict[str, Any]] = []
    try:
        dcm = pydicom.dcmread(str(file_path), stop_before_pixels=True, force=True)
    except Exception as e:
        return [
            {
                "layer": "ps3_15_tags",
                "code": "INVALID_DICOM",
                "message": f"Failed to parse DICOM: {e}",
                "location": str(file_path),
            }
        ]

    # Layer 1: Check standard PS3.15 tags
    for group, elem, tag_name in PS3_15_TAGS_TO_CHECK:
        tag = Tag(group, elem)
        if tag in dcm:
            data_elem = dcm[tag]
            val = data_elem.value
            if is_value_identifying(val):
                violations.append(
                    {
                        "layer": "ps3_15_tags",
                        "code": f"PS3_15_TAG_PRESENT_{tag_name.upper()}",
                        "message": f"Prohibited PS3.15 identifying tag present: {tag_name} (0x{group:04x}, 0x{elem:04x})",
                        "location": f"(0x{group:04x}, 0x{elem:04x}) {tag_name}",
                    }
                )

    # Layer 2: Check private vendor tags (odd groups)
    for data_elem in dcm.iterall():
        tag = data_elem.tag
        if tag.group % 2 == 1:  # Odd group -> Private tag
            if (tag.group, tag.element) not in PRIVATE_TAG_ALLOWLIST:
                violations.append(
                    {
                        "layer": "private_tags",
                        "code": "PRIVATE_TAG_PRESENT",
                        "message": f"Unvetted private vendor tag present: (0x{tag.group:04x}, 0x{tag.element:04x})",
                        "location": f"(0x{tag.group:04x}, 0x{tag.element:04x})",
                    }
                )

    return violations
