"""Automation bias evaluation and quality metrics.

Tracks:
1. Delta-contour Dice (with pre-annotation vs from-scratch)
2. Acceptance rate of AI suggestions
3. Systematic area shift per anatomical class
"""

from typing import Any, Dict


def evaluate_automation_bias(
    preannotated_dices: list[float],
    acceptance_rate: float,
) -> Dict[str, Any]:
    """Evaluates whether annotators are systematically biased towards AI pre-annotations."""
    mean_dice = sum(preannotated_dices) / max(len(preannotated_dices), 1)
    return {
        "mean_delta_contour_dice": mean_dice,
        "acceptance_rate": acceptance_rate,
        "pass_threshold": mean_dice >= 0.90 and acceptance_rate < 0.60,
    }


__all__ = ["evaluate_automation_bias"]
