"""Tests for the deterministic 4-layer de-identification scanner (osv/deid)."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from osv.deid import inspect_3d_defacing, inspect_burned_in_text, inspect_dicom_tags, scan, verify_no_phi


def _create_minimal_dicom(
    file_path: Path,
    patient_name: str | None = None,
    private_tag: tuple[int, int, bytes] | None = None,
) -> Path:
    """Helper to create a valid minimal DICOM file for testing."""
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.7"
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(file_path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID

    if patient_name:
        ds.PatientName = patient_name
    else:
        ds.PatientName = "ANONYMOUS"
        ds.PatientID = "ANON_001"

    if private_tag:
        group, elem, val = private_tag
        ds.add_new((group, elem), "OB", val)

    ds.save_as(str(file_path))
    return file_path


def test_layer1_dicom_clean_vs_phi(tmp_path: Path):
    clean_dcm = _create_minimal_dicom(tmp_path / "clean.dcm")
    violations_clean = inspect_dicom_tags(clean_dcm)
    assert violations_clean == []

    dirty_dcm = _create_minimal_dicom(tmp_path / "dirty.dcm", patient_name="Doe^John")
    violations_dirty = inspect_dicom_tags(dirty_dcm)
    assert len(violations_dirty) >= 1
    assert any(v["layer"] == "ps3_15_tags" and "PATIENTNAME" in v["code"] for v in violations_dirty)


def test_layer2_dicom_private_tags(tmp_path: Path):
    dirty_priv = _create_minimal_dicom(
        tmp_path / "private.dcm",
        private_tag=(0x0019, 0x1010, b"Hospital Internal ID: 99482"),
    )
    violations = inspect_dicom_tags(dirty_priv)
    assert any(v["layer"] == "private_tags" for v in violations)


def test_layer3_ocr_clean_vs_burned_in_text(tmp_path: Path):
    # Clean organic-looking image (smooth gradient)
    clean_img = np.zeros((480, 854, 3), dtype=np.uint8)
    clean_img[:, :] = (120, 80, 50)
    clean_path = tmp_path / "clean_frame.png"
    cv2.imwrite(str(clean_path), clean_img)

    violations_clean = inspect_burned_in_text(clean_path)
    assert violations_clean == []

    # Dirty image with burned-in patient text and date in corner
    dirty_img = clean_img.copy()
    cv2.putText(
        dirty_img,
        "PATIENT: JOHN DOE  DOB: 12/05/1975",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        dirty_img,
        "HOSPITAL CLINIC ST. MARY 14:30:22",
        (30, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    dirty_path = tmp_path / "dirty_frame.png"
    cv2.imwrite(str(dirty_path), dirty_img)

    violations_dirty = inspect_burned_in_text(dirty_path)
    assert len(violations_dirty) >= 1
    assert any(v["layer"] == "burned_in_ocr" for v in violations_dirty)


def test_layer4_defacing_indicators(tmp_path: Path):
    # Non-volumetric passes
    assert inspect_3d_defacing("frame_001.png") == []

    # Defaced volumetric head MRI passes
    defaced_path = tmp_path / "sub-01_brain_mri_defaced.nii.gz"
    defaced_path.touch()
    assert inspect_3d_defacing(defaced_path) == []

    # Raw cranial volume without defacing marker fails
    raw_head_path = tmp_path / "sub-01_cranial_ct.nii.gz"
    raw_head_path.touch()
    violations = inspect_3d_defacing(raw_head_path)
    assert len(violations) == 1
    assert violations[0]["layer"] == "defacing"


def test_verify_no_phi_integrated(tmp_path: Path):
    clean_path = tmp_path / "clean_frame.png"
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(str(clean_path), img)

    result = verify_no_phi(clean_path)
    assert result["clean"] is True
    assert result["violations"] == []


def test_scan_cli_end_to_end(tmp_path: Path, capsys):
    clean_path = tmp_path / "clean_sample.png"
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(str(clean_path), img)

    out_file = tmp_path / "deid-verdict.json"
    exit_code = scan.main([str(clean_path), "--out", str(out_file)])

    assert exit_code == 0
    written = json.loads(out_file.read_text(encoding="utf-8"))
    assert written["overall"] == "pass"
    assert written["violations_total"] == 0
    captured = capsys.readouterr()
    assert "PASS" in captured.out
