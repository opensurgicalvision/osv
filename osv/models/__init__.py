"""Baseline model architectures and Hugging Face Hub integration.

M1: 2D Instrument Segmentation (nnU-Net 2D / Mask2Former)
M2: 2D Anatomy Segmentation (SAM 2 fine-tuned)
M3: Phase Recognition (TeCNO / TCN on spatio-temporal features)
M4: 3D Preoperative Organ/Vascular Segmentation (nnU-Net 3D / TotalSegmentator)
M5: Surgical Desmoking & Image Restoration
"""

def list_baselines() -> dict[str, str]:
    """Returns catalog of OpenSurgicalVision baseline models."""
    return {
        "M1": "2D Instrument Segmentation",
        "M2": "2D Anatomy Segmentation",
        "M3": "Surgical Phase Recognition",
        "M4": "3D Preop Organ & Vascular CT Segmentation",
        "M5": "Surgical Desmoking & Restoration",
    }


__all__ = ["list_baselines"]
