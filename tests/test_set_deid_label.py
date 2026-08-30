"""Unit test for the pure label_for() logic in scripts/set_deid_label.py."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from set_deid_label import label_for  # noqa: E402


def test_pass_verdict_maps_to_pass_label():
    assert label_for({"overall": "pass"}) == "deid:pass"


def test_fail_verdict_maps_to_fail_label():
    assert label_for({"overall": "fail"}) == "deid:fail"


def test_missing_overall_key_defaults_to_fail_label():
    """Fail closed: an unparseable/incomplete verdict must never be treated as a pass."""
    assert label_for({}) == "deid:fail"
