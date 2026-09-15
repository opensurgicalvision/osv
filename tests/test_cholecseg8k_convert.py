"""Tests for CholecSeg8k dataset annotation and conversion logic."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from osv.datasets.cholecseg8k import (
    ANNOTATIONS_BLOCKED_REASON,
    FrameRecord,
    build_annotations,
    build_categories,
)


def test_categories_count_and_keys():
    categories = build_categories()
    assert len(categories) == 13
    assert [c["id"] for c in categories] == list(range(13))
    assert categories[0]["name"] == "Black Background"
    assert categories[1]["name"] == "Abdominal Wall"
    assert categories[2]["name"] == "Liver"
    assert categories[10]["name"] == "Gallbladder"


def test_build_annotations_refuses_without_explicit_mapping():
    """R-14 test: build_annotations must refuse to execute without an explicit,
    human-supplied mapping, preventing AI from defining anatomical classes."""
    record = FrameRecord(
        video_id="video01",
        clip_id="video01_00001",
        frame_id="00001",
        image_path="dummy.png",
        annotation_mask_path="dummy_mask.png",
        color_mask_path="dummy_color.png",
        watershed_mask_path="dummy_ws.png",
    )
    images = [{"id": 1, "file_name": "dummy.png"}]

    with pytest.raises(NotImplementedError) as excinfo:
        build_annotations([record], images)
    assert ANNOTATIONS_BLOCKED_REASON in str(excinfo.value)


def test_build_annotations_with_explicit_human_mapping(tmp_path: Path):
    """Verifies that the polygon/bbox extraction mechanism functions when an
    explicit mapping is passed into the converter by a human/test harness."""
    frame_dir = tmp_path / "CholecSeg8k" / "video01" / "video01_00001"
    frame_dir.mkdir(parents=True, exist_ok=True)

    img_path = frame_dir / "frame_00001_endo.png"
    mask_path = frame_dir / "frame_00001_endo_mask.png"
    color_mask_path = frame_dir / "frame_00001_endo_color_mask.png"
    ws_path = frame_dir / "frame_00001_endo_watershed_mask.png"

    # Synthetic image
    raw_img = np.zeros((480, 854, 3), dtype=np.uint8)
    cv2.imwrite(str(img_path), raw_img)
    cv2.imwrite(str(mask_path), raw_img)
    cv2.imwrite(str(color_mask_path), raw_img)

    # Synthetic watershed mask with regions 100 and 200
    ws_mask = np.zeros((480, 854), dtype=np.uint8)
    ws_mask[50:150, 50:150] = 100  # Region 1 (100x100 square)
    ws_mask[200:260, 200:300] = 200  # Region 2 (60x100 rectangle)
    cv2.imwrite(str(ws_path), ws_mask)

    record = FrameRecord(
        video_id="video01",
        clip_id="video01_00001",
        frame_id="00001",
        image_path=f"CholecSeg8k/video01/video01_00001/{img_path.name}",
        annotation_mask_path=str(mask_path),
        color_mask_path=str(color_mask_path),
        watershed_mask_path=str(ws_path),
    )

    images = [
        {
            "id": 1,
            "file_name": record.image_path,
            "width": 854,
            "height": 480,
            "video_id": "video01",
            "clip_id": "video01_00001",
            "frame_id": "00001",
            "split": "train",
        }
    ]

    # Injected test mapping
    test_mapping = {100: 2, 200: 10}
    annotations = build_annotations([record], images, pixel_to_category=test_mapping)
    assert len(annotations) == 2

    cat_ids = {ann["category_id"] for ann in annotations}
    assert cat_ids == {2, 10}

    ann_liver = next(a for a in annotations if a["category_id"] == 2)
    assert ann_liver["image_id"] == 1
    assert ann_liver["bbox"] == [50.0, 50.0, 100.0, 100.0]
    assert ann_liver["area"] > 0
    assert len(ann_liver["segmentation"][0]) >= 6
