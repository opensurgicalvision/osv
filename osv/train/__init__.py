"""Training pipelines, Hydra configurations, mixed-precision routines and MLflow tracking."""

from typing import Any


def get_default_trainer_config() -> dict[str, Any]:
    """Returns standard reproducible trainer setup."""
    return {
        "precision": "bf16",
        "gradient_checkpointing": True,
        "patient_stratified_kfold": 5,
        "deterministic": True,
    }


__all__ = ["get_default_trainer_config"]
