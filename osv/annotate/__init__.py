"""Annotation pipelines, SAM 2 pre-annotation helpers, and CVAT/Label Studio connectors."""

from typing import Any


def get_preannotation_pipeline() -> dict[str, Any]:
    """Returns configuration for assisted annotation with automation bias safeguards."""
    return {
        "preannotator": "SAM2",
        "control_frames_ratio": 0.10,
        "delta_contour_threshold": 0.90,
    }


__all__ = ["get_preannotation_pipeline"]
