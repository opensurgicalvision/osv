"""Tests for the segmentation metrics (osv/eval/metrics.py).

The arithmetic is the easy half. What these pin down is the reporting rule that
the CholecSeg8k split forces on us: three of the thirteen classes are absent
from one split or another, and a metric that scores an absent class as 0.0 and
averages it in produces a headline number that is simply wrong. Every test
below is about refusing to invent a measurement.
"""

from __future__ import annotations

import numpy as np
import pytest

from osv.eval import metrics as M


def cm_from(pred, target, n=3):
    return M.confusion_matrix(np.array(pred), np.array(target), n)


# --- the confusion matrix ---------------------------------------------------


def test_perfect_prediction_is_identity():
    cm = cm_from([0, 1, 2, 1], [0, 1, 2, 1])
    assert np.array_equal(cm, np.diag([1, 2, 1]))


def test_ignore_index_pixels_are_dropped_not_scored():
    # The watershed boundary (255) is not a 14th class; it must vanish entirely.
    cm = cm_from([0, 0, 1], [0, M.IGNORE_INDEX, 1])
    assert cm.sum() == 2, "ignored pixels leaked into the matrix"


def test_out_of_range_label_raises_rather_than_being_clipped():
    # A label outside the class range means the mapping is wrong; clipping it
    # would hide exactly the bug worth surfacing.
    with pytest.raises(ValueError):
        M.confusion_matrix(np.array([0]), np.array([7]), num_classes=3)


def test_shape_mismatch_raises():
    with pytest.raises(ValueError):
        M.confusion_matrix(np.zeros(4), np.zeros(5), num_classes=3)


# --- the rule: absent means N/A, never zero ---------------------------------


def test_absent_class_scores_none_not_zero():
    # Class 2 never appears in the ground truth.
    cm = cm_from([0, 1, 1], [0, 1, 1])
    assert M.per_class_iou(cm)[2] is None
    assert M.per_class_dice(cm)[2] is None


def test_absent_class_is_excluded_from_the_macro_average():
    cm = cm_from([0, 1, 1], [0, 1, 1])
    mean, scored, skipped = M.macro_iou(cm)
    assert (scored, skipped) == (2, 1)
    assert mean == pytest.approx(1.0), "an absent class must not drag a perfect score down"


def test_present_but_never_predicted_class_scores_zero_not_none():
    # This is the case that *should* be 0.0: the class is really there and the
    # model missed all of it. Confusing it with 'absent' would flatter the model.
    cm = cm_from([0, 0, 0], [0, 1, 1])
    ious = M.per_class_iou(cm)
    assert ious[1] == 0.0
    assert ious[2] is None


def test_macro_average_over_no_present_classes_is_nan_not_zero():
    cm = np.zeros((3, 3), dtype=np.int64)
    mean, scored, skipped = M.macro_iou(cm)
    assert scored == 0 and skipped == 3
    assert np.isnan(mean)


# --- the report -------------------------------------------------------------


def test_summary_labels_absent_classes_explicitly():
    cm = cm_from([0, 1, 1], [0, 1, 1])
    report = M.summarize(cm, ["Liver", "Gallbladder", "Hepatic Vein"])
    assert report["per_class"]["Hepatic Vein"]["status"].startswith("N/A")
    assert report["per_class"]["Liver"]["status"] == "ok"
    assert report["classes_skipped_absent"] == 1


def test_flattened_metrics_omit_absent_classes_entirely():
    # Logging iou_hepatic_vein=0.0 to a tracker would be a claim we cannot make.
    cm = cm_from([0, 1, 1], [0, 1, 1])
    flat = M.flatten_for_tracker(M.summarize(cm, ["Liver", "Gallbladder", "Hepatic Vein"]))
    assert "iou_liver" in flat
    assert not any("hepatic" in key for key in flat)


def test_flattened_metrics_carry_the_scored_class_count():
    # A macro number is meaningless without knowing what it averaged over.
    cm = cm_from([0, 1, 1], [0, 1, 1])
    flat = M.flatten_for_tracker(M.summarize(cm))
    assert flat["classes_scored"] == 2.0
    assert flat["classes_skipped_absent"] == 1.0


def test_iou_and_dice_agree_on_a_hand_checked_case():
    # truth: 2 px of class 1; pred: 1 correct, 1 leaked to class 0
    cm = cm_from([1, 0], [1, 1])
    iou = M.per_class_iou(cm)[1]
    dice = M.per_class_dice(cm)[1]
    assert iou == pytest.approx(0.5)          # 1 / (1 + 1)
    assert dice == pytest.approx(2 / 3)       # 2*1 / (1 + 2)
