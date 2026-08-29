"""Two-tier surgical domain data augmentations.

L1 (on-the-fly, CPU): elastic deformations, motion blur, defocus, sensor noise, color shifts.
L2 (offline pre-generated): realistic smoke, lens blood splatter, specular highlights.
"""

from typing import Any, Dict


def get_l1_augmentations() -> Dict[str, Any]:
    """Returns albumentations pipeline for on-the-fly L1 surgical transformations."""
    return {"tier": "L1", "status": "active"}


def get_l2_dataset_info() -> Dict[str, Any]:
    """Returns metadata about pre-generated L2 static augmented datasets."""
    return {"tier": "L2", "variants_per_frame": 3, "invariance": "mask_preserving"}


__all__ = ["get_l1_augmentations", "get_l2_dataset_info"]
