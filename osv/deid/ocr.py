"""Layer 3: OCR inspection for burned-in pixel text annotations.

Detects burned-in text (patient names, medical record numbers, timestamps,
hospital names, or operator identifiers) on endoscopic / laparoscopic /
ultrasound / radiological frames.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

try:
    import pytesseract  # type: ignore[import-untyped]
except ImportError:
    pytesseract = None  # type: ignore[assignment]


# Date / time / identifier patterns often found in burned-in medical video feeds
PHI_TEXT_PATTERNS = (
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),  # Dates like 12/04/2021
    re.compile(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"),  # Dates like 2021-04-12
    re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b"),  # Timestamps like 14:30:00
    re.compile(r"\b(?:patient|dob|mrn|dr|id|hospital|clinic|dept|age|sex)\b", re.IGNORECASE),
)


def _detect_text_with_tesseract(img_np: np.ndarray) -> list[str]:
    """Run Tesseract OCR if available and executable."""
    if pytesseract is None:
        return []
    try:
        text = pytesseract.image_to_string(img_np)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines
    except Exception:
        return []


def _detect_text_regions_opencv(img_np: np.ndarray) -> list[dict[str, Any]]:
    """Deterministic morphological / gradient text region detector.

    Surgical frames are predominantly organic tissues (smooth gradients).
    Burned-in text appears as sharp, high-frequency, high-contrast glyphs
    aligned horizontally with characteristic height (8-40px) and aspect ratio.
    """
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np

    h, w = gray.shape[:2]
    if h < 20 or w < 20:
        return []

    # Morphological gradient to isolate sharp intensity transitions (text strokes)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)

    # Otsu thresholding
    _, thresh = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Connect horizontally adjacent glyphs into text lines
    connect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
    connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, connect_kernel)

    contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detected_regions: list[dict[str, Any]] = []
    for c in contours:
        x, y, rw, rh = cv2.boundingRect(c)
        aspect = rw / float(rh) if rh > 0 else 0
        area = rw * rh
        # Text line characteristics: height 8-50px, width >= 25px, aspect >= 1.5,
        # occupying small fraction of frame (not the whole image)
        if 8 <= rh <= 60 and rw >= 25 and aspect >= 1.5 and area < (w * h * 0.25):
            # Check edge density / contrast inside bounding box
            roi = thresh[y : y + rh, x : x + rw]
            density = np.count_nonzero(roi) / float(area)
            if 0.15 <= density <= 0.85:
                detected_regions.append({"x": x, "y": y, "w": rw, "h": rh, "density": round(density, 3)})

    return detected_regions


def inspect_burned_in_text(image_input: str | Path | np.ndarray | Image.Image) -> list[dict[str, Any]]:
    """Inspect an image or frame for burned-in text / PHI overlay."""
    if isinstance(image_input, (str, Path)):
        file_path = Path(image_input)
        try:
            with Image.open(file_path) as pil_img:
                img_np = np.array(pil_img.convert("RGB"))
        except Exception as e:
            return [
                {
                    "layer": "burned_in_ocr",
                    "code": "IMAGE_READ_ERROR",
                    "message": f"Failed to load image for OCR scan: {e}",
                    "location": str(file_path),
                }
            ]
        location_str = str(file_path)
    elif isinstance(image_input, Image.Image):
        img_np = np.array(image_input.convert("RGB"))
        location_str = "PIL.Image"
    elif isinstance(image_input, np.ndarray):
        img_np = image_input
        location_str = "numpy.ndarray"
    else:
        return [
            {
                "layer": "burned_in_ocr",
                "code": "INVALID_IMAGE_INPUT",
                "message": f"Unsupported image input type: {type(image_input)}",
                "location": "unknown",
            }
        ]

    violations: list[dict[str, Any]] = []

    # 1. Tesseract OCR check (if available)
    ocr_lines = _detect_text_with_tesseract(img_np)
    for line in ocr_lines:
        for pattern in PHI_TEXT_PATTERNS:
            if pattern.search(line):
                violations.append(
                    {
                        "layer": "burned_in_ocr",
                        "code": "BURNED_IN_TEXT_DETECTED_OCR",
                        "message": f"Burned-in text pattern detected: '{line}'",
                        "location": location_str,
                    }
                )
                break

    # 2. Structural text-region candidate analysis (deterministic fallback)
    text_regions = _detect_text_regions_opencv(img_np)
    # If multiple distinct structured text regions or corner text blocks exist
    if len(text_regions) >= 2:
        violations.append(
            {
                "layer": "burned_in_ocr",
                "code": "BURNED_IN_TEXT_REGIONS_DETECTED",
                "message": f"Detected {len(text_regions)} high-contrast burned-in text region(s) in frame.",
                "location": f"{location_str} ({len(text_regions)} region(s))",
            }
        )

    return violations
