"""Evaluation harnesses, inter-rater metrics (Cohen/Fleiss kappa, Dice, IoU), and patient reports."""

import numpy as np


def compute_dice(pred_mask: np.ndarray, gt_mask: np.ndarray, eps: float = 1e-6) -> float:
    """Computes Dice similarity coefficient between two binary masks."""
    intersection = np.sum(pred_mask * gt_mask)
    return float((2.0 * intersection + eps) / (np.sum(pred_mask) + np.sum(gt_mask) + eps))


__all__ = ["compute_dice"]
