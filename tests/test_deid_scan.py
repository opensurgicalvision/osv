"""Tests for the deterministic de-identification scan CLI (osv/deid/scan.py).

verify_no_phi is still a stub (always clean=True, see osv/deid/__init__.py),
so these tests exercise the real part: aggregation into the schema
deid-gate.md documents, the JSON artifact written to disk, and the exit code
the Stage A workflow gates on. Monkeypatching verify_no_phi lets the FAIL
path be tested honestly without waiting on the Phase 1 OCR/DICOM work.
"""

import json

from osv.deid import scan


def test_scan_files_passes_when_stub_reports_clean(tmp_path):
    verdict = scan.scan_files(["case_001.dcm", "case_002.dcm"])

    assert verdict["overall"] == "pass"
    assert verdict["violations_total"] == 0
    assert verdict["files_scanned"] == ["case_001.dcm", "case_002.dcm"]
    assert set(verdict["layers"]) == set(scan.LAYER_NAMES)


def test_scan_files_fails_and_buckets_by_layer(monkeypatch):
    def fake_verify(file_path):
        if file_path == "case_bad.dcm":
            return {
                "file_path": file_path,
                "clean": False,
                "violations": [
                    {"layer": "burned_in_ocr", "detail": "patient name visible in frame 42"},
                    {"layer": "private_tags", "detail": "group 0x0009 not stripped"},
                ],
            }
        return {"file_path": file_path, "clean": True, "violations": []}

    monkeypatch.setattr(scan, "verify_no_phi", fake_verify)

    verdict = scan.scan_files(["case_ok.dcm", "case_bad.dcm"])

    assert verdict["overall"] == "fail"
    assert verdict["violations_total"] == 2
    assert len(verdict["layers"]["burned_in_ocr"]) == 1
    assert verdict["layers"]["burned_in_ocr"][0]["file"] == "case_bad.dcm"
    assert len(verdict["layers"]["private_tags"]) == 1
    assert verdict["layers"]["ps3_15_tags"] == []


def test_main_writes_verdict_json_and_returns_zero_on_pass(tmp_path, capsys):
    out_file = tmp_path / "deid-verdict.json"

    exit_code = scan.main(["case_001.dcm", "--out", str(out_file)])

    assert exit_code == 0
    written = json.loads(out_file.read_text(encoding="utf-8"))
    assert written["overall"] == "pass"
    captured = capsys.readouterr()
    assert "PASS" in captured.out


def test_main_returns_nonzero_on_fail(tmp_path, monkeypatch):
    def fake_verify(file_path):
        return {"file_path": file_path, "clean": False, "violations": [{"layer": "defacing", "detail": "face reconstructable"}]}

    monkeypatch.setattr(scan, "verify_no_phi", fake_verify)
    out_file = tmp_path / "deid-verdict.json"

    exit_code = scan.main(["head_ct.nii", "--out", str(out_file)])

    assert exit_code == 1
    written = json.loads(out_file.read_text(encoding="utf-8"))
    assert written["overall"] == "fail"
