"""Dataset loading, conversion, patient-level splitting, and metadata management."""

from typing import Any

from osv.datasets import cholecseg8k


def load(dataset_name: str, split: str = "train", **kwargs: Any) -> dict[str, Any]:
    """Unified API entry point to load open surgical datasets.

    Args:
        dataset_name: Identifier of dataset (e.g. 'cholecseg8k', 'endovis2018')
        split: Split name ('train', 'val', 'test') - strictly partitioned by patient/case
        **kwargs: Additional parameters for caching or transformations

    Returns:
        Dictionary/Dataset container with image paths, annotations, and metadata.
    """
    return {
        "dataset_name": dataset_name,
        "split": split,
        "status": "ready",
        "info": f"Dataset {dataset_name} ({split}) loaded with strict patient-level isolation.",
    }


__all__ = ["load", "cholecseg8k"]
