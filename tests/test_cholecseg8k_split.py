"""R-08 leakage tests for the CholecSeg8k patient-level split.

These tests never require the ~3GB raw archive to be present: the split
algorithm is exercised against the real per-video frame counts (recorded
once, by hand, from the manifest-verified archive — see
osv/datasets/splits/cholecseg8k.json), and the committed split definition
itself is checked directly. This is what CI's `test_no_patient_leakage`
actually runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from osv.datasets import cholecseg8k

SPLIT_DEFINITION_PATH = (
    Path(__file__).resolve().parents[1] / "osv" / "datasets" / "splits" / "cholecseg8k.json"
)

# The real per-video frame counts, enumerated from the manifest-declared,
# checksum-verified CholecSeg8k.zip (17 videos, 8,080 frames total).
REAL_VIDEO_FRAME_COUNTS = {
    "video01": 1280,
    "video09": 240,
    "video12": 640,
    "video17": 320,
    "video18": 160,
    "video20": 160,
    "video24": 960,
    "video25": 320,
    "video26": 320,
    "video27": 400,
    "video28": 560,
    "video35": 240,
    "video37": 480,
    "video43": 720,
    "video48": 240,
    "video52": 800,
    "video55": 240,
}


class _ConflictingAssignment:
    """A Mapping-like stand-in that yields the same video_id under two
    different splits via .items() — the one shape a real dict can never
    take, used to prove assert_no_patient_leakage actually detects a
    genuine leak rather than being a no-op that a dict's key-uniqueness
    makes trivially pass."""

    def items(self):
        return [("video01", "train"), ("video01", "test")]


def test_no_patient_leakage():
    """The actual R-08 gate: no video appears in more than one split, for
    both a freshly computed split and the committed split definition."""
    assignment = cholecseg8k.build_patient_split(REAL_VIDEO_FRAME_COUNTS)
    cholecseg8k.assert_no_patient_leakage(assignment)  # raises on violation

    assert set(assignment) == set(REAL_VIDEO_FRAME_COUNTS)
    assert set(assignment.values()) <= {"train", "val", "test"}

    committed = json.loads(SPLIT_DEFINITION_PATH.read_text(encoding="utf-8"))
    committed_assignment = committed["assignment"]
    cholecseg8k.assert_no_patient_leakage(committed_assignment)

    by_split: dict[str, set[str]] = {}
    for video_id, split in committed_assignment.items():
        by_split.setdefault(split, set()).add(video_id)
    train, val, test = by_split.get("train", set()), by_split.get("val", set()), by_split.get("test", set())
    assert not (train & val)
    assert not (train & test)
    assert not (val & test)


def test_assert_no_patient_leakage_detects_a_genuine_violation():
    with pytest.raises(AssertionError, match="R-08 VIOLATION"):
        cholecseg8k.assert_no_patient_leakage(_ConflictingAssignment())


def test_split_is_deterministic():
    """Same input, same output — required for a reproducible, auditable split."""
    first = cholecseg8k.build_patient_split(REAL_VIDEO_FRAME_COUNTS)
    second = cholecseg8k.build_patient_split(dict(REAL_VIDEO_FRAME_COUNTS))
    assert first == second


def test_split_covers_every_video_exactly_once():
    assignment = cholecseg8k.build_patient_split(REAL_VIDEO_FRAME_COUNTS)
    assert len(assignment) == len(REAL_VIDEO_FRAME_COUNTS) == cholecseg8k.EXPECTED_VIDEO_COUNT


def test_split_ratios_are_reasonably_respected():
    assignment = cholecseg8k.build_patient_split(REAL_VIDEO_FRAME_COUNTS)
    totals = cholecseg8k.split_frame_counts(REAL_VIDEO_FRAME_COUNTS, assignment)
    total_frames = sum(REAL_VIDEO_FRAME_COUNTS.values())
    assert total_frames == cholecseg8k.EXPECTED_FRAME_COUNT

    # Loose tolerance: with only 17 videos of very unequal size, exact 70/15/15
    # is unreachable, but no split should be starved or dominate entirely.
    assert 0.55 <= totals["train"] / total_frames <= 0.80
    assert 0.05 <= totals["val"] / total_frames <= 0.25
    assert 0.05 <= totals["test"] / total_frames <= 0.25
