"""Semantic-segmentation metrics for the OSV benchmark.

RESEARCH USE ONLY - NOT FOR CLINICAL USE.

Per-class IoU and Dice accumulated through a confusion matrix, plus one rule
this project cares about more than the arithmetic:

    A class that does not occur in the evaluation split has NO score.
    It is reported as None (N/A) - never as 0.0, never as 1.0.

That is not pedantry. CholecSeg8k's rare classes sit inside single videos while
R-08 requires the split to cut by video, so three of the thirteen classes are
absent from train or from test entirely (see docs/data-cards/cholecseg8k.md,
section 4a). Scoring an absent class as 0.0 and folding it into a macro average
silently drags the headline number down and makes a model look worse than it
is; scoring it as 1.0 flatters it the same way. Neither is a measurement.

`macro_iou` therefore averages only over classes that are actually present, and
reports how many it skipped so a reader can never mistake a 10-class average
for a 13-class one.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

IGNORE_INDEX = 255


def confusion_matrix(
    pred: np.ndarray,
    target: np.ndarray,
    num_classes: int,
    ignore_index: int = IGNORE_INDEX,
) -> np.ndarray:
    """Accumulate a `num_classes x num_classes` confusion matrix (rows = truth).

    Pixels whose ground truth is `ignore_index` are dropped, which is how the
    watershed boundary (255) stays out of the score instead of being counted as
    a 14th class.
    """
    pred = np.asarray(pred).reshape(-1)
    target = np.asarray(target).reshape(-1)
    if pred.shape != target.shape:
        raise ValueError(f"pred/target shape mismatch: {pred.shape} vs {target.shape}")

    keep = target != ignore_index
    pred, target = pred[keep], target[keep]

    out_of_range = (pred >= num_classes) | (pred < 0) | (target >= num_classes) | (target < 0)
    if out_of_range.any():
        raise ValueError(
            f"label(s) outside [0, {num_classes}) found after dropping ignore_index; "
            "this is a mapping bug, not something to clip away"
        )

    idx = target.astype(np.int64) * num_classes + pred.astype(np.int64)
    return np.bincount(idx, minlength=num_classes**2).reshape(num_classes, num_classes)


def _support(cm: np.ndarray) -> np.ndarray:
    """Ground-truth pixel count per class - the basis for 'present or not'."""
    return cm.sum(axis=1)


def per_class_iou(cm: np.ndarray) -> list[float | None]:
    """IoU per class; None where the class has no ground-truth pixels at all."""
    tp = np.diag(cm).astype(np.float64)
    union = cm.sum(axis=0) + cm.sum(axis=1) - np.diag(cm)
    support = _support(cm)
    return [
        None if support[i] == 0 else (float(tp[i] / union[i]) if union[i] > 0 else 0.0)
        for i in range(cm.shape[0])
    ]


def per_class_dice(cm: np.ndarray) -> list[float | None]:
    """Dice per class; None where the class has no ground-truth pixels at all."""
    tp = np.diag(cm).astype(np.float64)
    denom = cm.sum(axis=0) + cm.sum(axis=1)
    support = _support(cm)
    return [
        None if support[i] == 0 else (float(2.0 * tp[i] / denom[i]) if denom[i] > 0 else 0.0)
        for i in range(cm.shape[0])
    ]


def macro_iou(cm: np.ndarray) -> tuple[float, int, int]:
    """Mean IoU over *present* classes only.

    Returns `(mean, scored, skipped)`. The two counts are part of the result on
    purpose: a bare number cannot tell you it was averaged over 10 of 13
    classes, and that difference has misled more than one benchmark table.
    """
    values = [v for v in per_class_iou(cm) if v is not None]
    skipped = cm.shape[0] - len(values)
    if not values:
        return float("nan"), 0, skipped
    return float(np.mean(values)), len(values), skipped


def pixel_accuracy(cm: np.ndarray) -> float:
    total = cm.sum()
    return float(np.diag(cm).sum() / total) if total else float("nan")


def summarize(
    cm: np.ndarray,
    class_names: Sequence[str] | Mapping[int, str] | None = None,
) -> dict[str, Any]:
    """Full report: per-class IoU/Dice/support, macro IoU, and what was skipped."""
    n = cm.shape[0]
    if class_names is None:
        names = [str(i) for i in range(n)]
    elif isinstance(class_names, Mapping):
        names = [class_names.get(i, str(i)) for i in range(n)]
    else:
        names = list(class_names)

    ious = per_class_iou(cm)
    dices = per_class_dice(cm)
    support = _support(cm)
    mean_iou, scored, skipped = macro_iou(cm)

    return {
        "macro_iou": mean_iou,
        "classes_scored": scored,
        "classes_skipped_absent": skipped,
        "pixel_accuracy": pixel_accuracy(cm),
        "per_class": {
            names[i]: {
                "iou": ious[i],
                "dice": dices[i],
                "support_px": int(support[i]),
                "status": "ok" if support[i] else "N/A - absent from this split",
            }
            for i in range(n)
        },
    }


def flatten_for_tracker(report: Mapping[str, Any], prefix: str = "") -> dict[str, float]:
    """Flatten `summarize()` into scalar metrics a tracker can log.

    Classes reported as N/A are omitted entirely rather than logged as 0.0 - an
    absent metric is honest, a zero is a claim.
    """
    out: dict[str, float] = {}
    for key in ("macro_iou", "pixel_accuracy"):
        value = report.get(key)
        if value is not None and not (isinstance(value, float) and np.isnan(value)):
            out[f"{prefix}{key}"] = float(value)
    for key in ("classes_scored", "classes_skipped_absent"):
        if key in report:
            out[f"{prefix}{key}"] = float(report[key])
    for name, entry in report.get("per_class", {}).items():
        slug = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_").lower()
        for metric in ("iou", "dice"):
            if entry.get(metric) is not None:
                out[f"{prefix}{metric}_{slug}"] = float(entry[metric])
    return out


__all__ = [
    "IGNORE_INDEX",
    "confusion_matrix",
    "per_class_iou",
    "per_class_dice",
    "macro_iou",
    "pixel_accuracy",
    "summarize",
    "flatten_for_tracker",
]
