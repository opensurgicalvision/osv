"""Edge-case benchmark suite: smoke levels, blood on lens, defocus, overexposure, and motion blur."""

from typing import Any, Dict, List


def list_robustness_perturbations() -> List[str]:
    """Returns catalog of standard surgical stress tests."""
    return [
        "smoke_light",
        "smoke_dense",
        "blood_splatter",
        "lens_defocus",
        "specular_glare",
        "motion_blur",
        "rare_anatomy_anomaly",
    ]


__all__ = ["list_robustness_perturbations"]
