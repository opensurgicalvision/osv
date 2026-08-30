"""Deterministic converter for the CholecSeg8k dataset.

RESEARCH USE ONLY — NOT FOR CLINICAL USE.

Source: Hugging Face `minwoosun/CholecSeg8k` (pinned revision, see
`osv/datasets/manifests/cholecseg8k.yaml`), itself a semantic-segmentation
annotation of a 17-video subset of Cholec80 (CAMMA / University of
Strasbourg / IRCAD).

Citation (carry verbatim wherever this dataset is used, per its
CC BY-NC-SA 4.0 attribution clause):

    Hong, W.-Y., Kao, C.-L., Kuo, Y.-H., Wang, J.-R., Chang, W.-L., Shih, C.-S.
    (2020). CholecSeg8k: A Semantic Segmentation Dataset for Laparoscopic
    Cholecystectomy Based on Cholec80. arXiv:2012.12453.

This module does exactly the deterministic, no-judgment-call part of
onboarding (per the `data-butler` agent contract and the `dataset-onboard`
skill):

  * parses the archive's real on-disk layout (`CholecSeg8k/videoNN/
    videoNN_XXXXX/frame_YYYYY_endo*.png`) and validates it against the
    `folder_prefix` / `videoNN` patient-id assumption declared in the
    manifest (R-08: the split key is the *video*, i.e. one source Cholec80
    operation — never a frame);
  * builds a deterministic, whole-video (never whole-frame) train/val/test
    split;
  * emits a COCO-like `instances.json` skeleton: `images` + `categories`
    (the 13 published classes, Table I of the paper above) fully populated.

KNOWN, DELIBERATE GAP — read before extending this module
-----------------------------------------------------------
`annotations` (the actual per-pixel segmentation) are intentionally **not**
emitted by this converter yet. The archive's `*_endo_watershed_mask.png` /
`*_endo_mask.png` files do *not* use the simple "pixel value == class ID
0..12" encoding the paper's prose claims — empirically (see the onboarding
MR discussion) the raw grayscale values observed are things like
{0, 11, 12, 13, 21, 22, 23, 24, 25, 31, 32, 33, 50, 255, ...}, clustered in
bands rather than 13 flat values, and neither the archive, the arXiv paper
(no machine-readable table), the HF dataset card, nor the HF loading script
(`CholecSeg8k.py`, which just yields raw file paths) publish a pixel-value
(or `color_mask` RGB) -> class-ID lookup table.

Inventing that table from a low-resolution reading of the paper's example
figures would mean an AI agent silently deciding which pixels are "Liver"
vs. "Gallbladder" vs. "Grasper" — squarely the "defining anatomical classes"
line this project reserves for a human / the Clinical Lead (RC), not
something to guess into a benchmark's ground truth. `build_annotations`
below is therefore written to require an explicit, human-supplied
`color_to_category` mapping and to refuse to run without one, rather than
default to a guess.

Once a human sources the authoritative mapping (e.g. from the dataset
authors, or a citable reference implementation), pass it to `convert()` and
the `images`/`categories`/split machinery here does not need to change.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import cv2
import numpy as np
from PIL import Image



# ---------------------------------------------------------------------------
# Categories — Table I, Hong et al. (2020), arXiv:2012.12453. Transcribed
# verbatim from the published paper, not invented here.
# ---------------------------------------------------------------------------

CATEGORIES: tuple[dict[str, Any], ...] = (
    {"id": 0, "name": "Black Background"},
    {"id": 1, "name": "Abdominal Wall"},
    {"id": 2, "name": "Liver"},
    {"id": 3, "name": "Gastrointestinal Tract"},
    {"id": 4, "name": "Fat"},
    {"id": 5, "name": "Grasper"},
    {"id": 6, "name": "Connective Tissue"},
    {"id": 7, "name": "Blood"},
    {"id": 8, "name": "Cystic Duct"},
    {"id": 9, "name": "L-hook Electrocautery"},
    {"id": 10, "name": "Gallbladder"},
    {"id": 11, "name": "Hepatic Vein"},
    {"id": 12, "name": "Liver Ligament"},
)

ANNOTATIONS_BLOCKED_REASON = (
    "No verified pixel-value/color -> class-ID lookup table is available "
    "for CholecSeg8k's watershed/annotation masks from any allowlisted, "
    "deterministic source (archive contents, arXiv:2012.12453, the HF "
    "dataset card, or the HF loading script). Per the project's ban on an "
    "AI agent defining anatomical classes (R-14 / Clinical Lead authority), "
    "this converter refuses to guess one. Supply a verified `pixel_to_category` "
    "or `color_to_category` mapping to `build_annotations()` / `convert()` "
    "once a human / Clinical Lead has sourced and approved the authoritative mapping."
)


EXPECTED_VIDEO_COUNT = 17

EXPECTED_FRAME_COUNT = 8080
IMAGE_WIDTH = 854
IMAGE_HEIGHT = 480

_FRAME_RE = re.compile(r"^CholecSeg8k/(video\d+)/(video\d+_\d+)/frame_(\d+)_endo\.png$")
_MASK_SUFFIXES = ("_endo_mask.png", "_endo_color_mask.png", "_endo_watershed_mask.png")


@dataclass(frozen=True)
class FrameRecord:
    """One annotated CholecSeg8k frame and its three mask variants.

    `video_id` is the R-08 patient/operation/session key (manifest's
    `folder_prefix` / `videoNN` strategy) — never `frame_id`.
    """

    video_id: str
    clip_id: str
    frame_id: str
    image_path: str
    annotation_mask_path: str
    color_mask_path: str
    watershed_mask_path: str


def patient_id(record: FrameRecord) -> str:
    """R-08 split key: the source Cholec80 video/operation, not the frame."""
    return record.video_id


# ---------------------------------------------------------------------------
# Layout parsing
# ---------------------------------------------------------------------------


def iter_frames_from_zip(zip_path: str | Path) -> Iterator[FrameRecord]:
    """Walk the manifest-declared archive and yield one record per annotated
    frame, validating that all three mask variants are present alongside the
    raw frame. Raises ValueError (a manifest bug, not a fallback) if the
    layout does not match the `videoNN/videoNN_XXXXX/frame_*_endo.png`
    pattern the manifest's `patient_id_field` assumes.
    """
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        yield from _records_from_names(names)


def iter_frames_from_dir(root: str | Path) -> Iterator[FrameRecord]:
    """Same as `iter_frames_from_zip`, for an already-extracted directory
    tree whose root is the `CholecSeg8k/` folder's *parent*.
    """
    root = Path(root)
    names = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*.png")
    }
    yield from _records_from_names(names)


def _records_from_names(names: set[str]) -> Iterator[FrameRecord]:
    frame_names = sorted(n for n in names if _FRAME_RE.match(n))
    if not frame_names:
        raise ValueError(
            "No files matched 'CholecSeg8k/videoNN/videoNN_XXXXX/frame_*_endo.png'. "
            "This is a manifest bug (patient_id_field.pattern), not a fallback case."
        )

    for name in frame_names:
        match = _FRAME_RE.match(name)
        assert match is not None
        video_id, clip_id, frame_id = match.groups()
        base = name[: -len("_endo.png")]
        mask_paths = [f"{base}{suffix}" for suffix in _MASK_SUFFIXES]
        missing = [m for m in mask_paths if m not in names]
        if missing:
            raise ValueError(
                f"Frame '{name}' is missing expected mask file(s) {missing}. "
                "This is a manifest/layout bug, not a fallback case."
            )
        yield FrameRecord(
            video_id=video_id,
            clip_id=clip_id,
            frame_id=frame_id,
            image_path=name,
            annotation_mask_path=mask_paths[0],
            color_mask_path=mask_paths[1],
            watershed_mask_path=mask_paths[2],
        )


def validate_layout(records: Sequence[FrameRecord]) -> None:
    """Cross-check the parsed archive against the manifest's declared
    expectations. Raises ValueError (never silently continues) on mismatch.
    """
    video_ids = {r.video_id for r in records}
    if len(video_ids) != EXPECTED_VIDEO_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_VIDEO_COUNT} source videos per the manifest, "
            f"found {len(video_ids)}: {sorted(video_ids)}. Manifest bug — stop, do not improvise."
        )
    if len(records) != EXPECTED_FRAME_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_FRAME_COUNT} annotated frames per the manifest, "
            f"found {len(records)}. Manifest bug — stop, do not improvise."
        )


# ---------------------------------------------------------------------------
# Patient-level split (R-08)
# ---------------------------------------------------------------------------


def build_patient_split(
    video_frame_counts: Mapping[str, int],
    ratios: Mapping[str, float] | None = None,
) -> dict[str, str]:
    """Assign whole videos (never frames) to train/val/test.

    Deterministic largest-first bin-packing: videos are visited in
    descending frame-count order (ties broken by ascending video_id for
    reproducibility) and each is assigned to whichever split is currently
    furthest below its target share of the total. This never splits a
    single video across two bins, which is what makes frame-level leakage
    structurally impossible rather than merely tested-for.
    """
    ratios = dict(ratios or {"train": 0.70, "val": 0.15, "test": 0.15})
    if abs(sum(ratios.values()) - 1.0) > 1e-6:
        raise ValueError(f"Split ratios must sum to 1.0, got {ratios}")

    total_frames = sum(video_frame_counts.values())
    targets = {split: ratio * total_frames for split, ratio in ratios.items()}
    loaded: dict[str, int] = {split: 0 for split in ratios}

    ordered = sorted(video_frame_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    assignment: dict[str, str] = {}
    for video_id, count in ordered:
        # Deficit = how far below target (as a fraction of target) each
        # split currently is; assign to the most-underfilled split.
        split = max(
            ratios,
            key=lambda s: (targets[s] - loaded[s]) / targets[s] if targets[s] > 0 else -1.0,
        )
        assignment[video_id] = split
        loaded[split] += count

    return assignment


def split_frame_counts(
    video_frame_counts: Mapping[str, int], assignment: Mapping[str, str]
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for video_id, count in video_frame_counts.items():
        split = assignment[video_id]
        totals[split] = totals.get(split, 0) + count
    return totals


def assert_no_patient_leakage(assignment: Mapping[str, str]) -> None:
    """The actual R-08 leakage check: every video_id maps to exactly one
    split by construction of a dict, so the only way to violate R-08 here
    is duplicate *keys* feeding the assignment in the first place. Kept as
    an explicit, named check (rather than relying on dict semantics alone)
    so `/split-check` and CI have something to call and quote.
    """
    videos_seen: dict[str, str] = {}
    for video_id, split in assignment.items():
        if video_id in videos_seen and videos_seen[video_id] != split:
            raise AssertionError(
                f"R-08 VIOLATION: video '{video_id}' assigned to both "
                f"'{videos_seen[video_id]}' and '{split}'."
            )
        videos_seen[video_id] = split


# ---------------------------------------------------------------------------
# COCO-like conversion
# ---------------------------------------------------------------------------


def _image_size(zf: zipfile.ZipFile | None, path: str) -> tuple[int, int]:
    from PIL import Image

    if zf is not None:
        with zf.open(path) as fh:
            with Image.open(io.BytesIO(fh.read())) as im:
                return im.size
    with Image.open(path) as im:
        return im.size


def build_categories() -> list[dict[str, Any]]:
    return [dict(c) for c in CATEGORIES]


def build_images(
    records: Sequence[FrameRecord],
    assignment: Mapping[str, str],
    *,
    zip_path: str | Path | None = None,
    verify_dimensions: bool = True,
) -> list[dict[str, Any]]:
    """Build the COCO-like `images` list. Verifies every frame is really
    854x480 rather than trusting the manifest's stated resolution."""
    images: list[dict[str, Any]] = []
    zf = zipfile.ZipFile(zip_path) if zip_path is not None else None
    try:
        for idx, record in enumerate(
            sorted(records, key=lambda r: (r.video_id, r.clip_id, r.frame_id))
        ):
            if verify_dimensions:
                width, height = _image_size(zf, record.image_path)
                if (width, height) != (IMAGE_WIDTH, IMAGE_HEIGHT):
                    raise ValueError(
                        f"Frame '{record.image_path}' is {width}x{height}, expected "
                        f"{IMAGE_WIDTH}x{IMAGE_HEIGHT} per the manifest. Manifest bug."
                    )
            else:
                width, height = IMAGE_WIDTH, IMAGE_HEIGHT
            images.append(
                {
                    "id": idx,
                    "file_name": record.image_path,
                    "width": width,
                    "height": height,
                    "video_id": record.video_id,
                    "clip_id": record.clip_id,
                    "frame_id": record.frame_id,
                    "split": assignment[record.video_id],
                }
            )
    finally:
        if zf is not None:
            zf.close()
    return images


def _load_mask_array(zf: zipfile.ZipFile | None, path: str) -> np.ndarray:
    if zf is not None:
        with zf.open(path) as fh:
            with Image.open(io.BytesIO(fh.read())) as im:
                return np.array(im)
    with Image.open(path) as im:
        return np.array(im)


def build_annotations(
    records: Sequence[FrameRecord],
    images: Sequence[dict[str, Any]],
    *,
    pixel_to_category: Mapping[int, int] | None = None,
    color_to_category: Mapping[tuple[int, int, int], int] | None = None,
    zip_path: str | Path | None = None,
    min_area: float = 4.0,
) -> list[dict[str, Any]]:
    """Generate COCO polygon annotations from segmentation masks.

    Requires an explicit, human-verified `pixel_to_category` or `color_to_category`
    mapping. Raises NotImplementedError if neither is supplied, adhering strictly
    to R-14 (AI agents are forbidden from defining anatomical classes).
    """
    if pixel_to_category is None and color_to_category is None:
        raise NotImplementedError(ANNOTATIONS_BLOCKED_REASON)

    annotations: list[dict[str, Any]] = []
    ann_id = 1

    image_id_by_path = {img["file_name"]: img["id"] for img in images}

    zf = zipfile.ZipFile(zip_path) if zip_path is not None else None
    try:
        for record in sorted(records, key=lambda r: (r.video_id, r.clip_id, r.frame_id)):
            img_id = image_id_by_path[record.image_path]

            if pixel_to_category is not None:
                mask_arr = _load_mask_array(zf, record.watershed_mask_path)
                if len(mask_arr.shape) == 3 and mask_arr.shape[2] == 3:
                    mask_2d = mask_arr[:, :, 0]
                else:
                    mask_2d = mask_arr

                unique_vals = np.unique(mask_2d)
                for pixel_val, cat_id in pixel_to_category.items():
                    if pixel_val not in unique_vals:
                        continue
                    bin_mask = (mask_2d == pixel_val).astype(np.uint8)
                    contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    for contour in contours:
                        area = float(cv2.contourArea(contour))
                        if area < min_area or len(contour) < 3:
                            continue
                        x, y, w, h = cv2.boundingRect(contour)
                        poly = [float(coord) for pt in contour for coord in pt[0]]
                        if len(poly) >= 6:
                            annotations.append(
                                {
                                    "id": ann_id,
                                    "image_id": img_id,
                                    "category_id": cat_id,
                                    "segmentation": [poly],
                                    "area": area,
                                    "bbox": [float(x), float(y), float(w), float(h)],
                                    "iscrowd": 0,
                                }
                            )
                            ann_id += 1
            elif color_to_category is not None:
                mask_arr = _load_mask_array(zf, record.color_mask_path)
                for color_tuple, cat_id in color_to_category.items():
                    bin_mask = np.all(mask_arr[:, :, :3] == color_tuple, axis=-1).astype(np.uint8)
                    if not np.any(bin_mask):
                        continue
                    contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    for contour in contours:
                        area = float(cv2.contourArea(contour))
                        if area < min_area or len(contour) < 3:
                            continue
                        x, y, w, h = cv2.boundingRect(contour)
                        poly = [float(coord) for pt in contour for coord in pt[0]]
                        if len(poly) >= 6:
                            annotations.append(
                                {
                                    "id": ann_id,
                                    "image_id": img_id,
                                    "category_id": cat_id,
                                    "segmentation": [poly],
                                    "area": area,
                                    "bbox": [float(x), float(y), float(w), float(h)],
                                    "iscrowd": 0,
                                }
                            )
                            ann_id += 1
    finally:
        if zf is not None:
            zf.close()

    return annotations


@dataclass
class ConversionResult:
    instances: dict[str, Any]
    split_assignment: dict[str, str]
    split_frame_totals: dict[str, int]
    video_frame_counts: dict[str, int]
    annotations_status: str


def convert(
    source: str | Path,
    out_dir: str | Path,
    *,
    ratios: Mapping[str, float] | None = None,
    pixel_to_category: Mapping[int, int] | None = None,
    color_to_category: Mapping[tuple[int, int, int], int] | None = None,
    verify_dimensions: bool = True,
) -> ConversionResult:
    """Deterministic end-to-end conversion.

    `source` is the manifest-declared zip (or an already-extracted
    directory). `out_dir` is a DVC-stage output directory — never
    `data/raw/`, never committed to git directly (R-01/R-02/R-23).
    """
    source = Path(source)
    is_zip = source.is_file() and source.suffix == ".zip"

    records = list(iter_frames_from_zip(source) if is_zip else iter_frames_from_dir(source))
    validate_layout(records)

    video_frame_counts: dict[str, int] = {}
    for r in records:
        video_frame_counts[patient_id(r)] = video_frame_counts.get(patient_id(r), 0) + 1

    assignment = build_patient_split(video_frame_counts, ratios=ratios)
    assert_no_patient_leakage(assignment)
    totals = split_frame_counts(video_frame_counts, assignment)

    images = build_images(
        records,
        assignment,
        zip_path=source if is_zip else None,
        verify_dimensions=verify_dimensions,
    )

    if pixel_to_category is None and color_to_category is None:
        annotations: list[dict[str, Any]] = []
        annotations_status = "blocked_pending_color_class_mapping"
    else:
        annotations = build_annotations(
            records,
            images,
            pixel_to_category=pixel_to_category,
            color_to_category=color_to_category,
            zip_path=source if is_zip else None,
        )
        annotations_status = "generated"

    instances = {
        "info": {
            "dataset": "cholecseg8k",
            "citation": "Hong et al. (2020), arXiv:2012.12453",
            "license": "CC BY-NC-SA 4.0",
            "annotations_status": annotations_status,
        },
        "categories": build_categories(),
        "images": images,
        "annotations": annotations,
    }

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "instances.json").write_text(json.dumps(instances, indent=2) + "\n", encoding="utf-8")

    split_doc = {
        "dataset": "cholecseg8k",
        "patient_id_field": {"strategy": "folder_prefix", "pattern": "videoNN"},
        "ratios": dict(ratios or {"train": 0.70, "val": 0.15, "test": 0.15}),
        "video_frame_counts": video_frame_counts,
        "assignment": assignment,
        "split_frame_totals": totals,
    }
    (out_dir / "split.json").write_text(json.dumps(split_doc, indent=2) + "\n", encoding="utf-8")

    return ConversionResult(
        instances=instances,
        split_assignment=assignment,
        split_frame_totals=totals,
        video_frame_counts=video_frame_counts,
        annotations_status=annotations_status,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=os.environ.get("CHOLECSEG8K_RAW_ZIP"),
        help="Path to CholecSeg8k.zip or an extracted directory. Falls back to "
        "the CHOLECSEG8K_RAW_ZIP environment variable (read here in Python, "
        "never shell-expanded, so a dvc.yaml stage cmd works identically on "
        "any OS/shell).",
    )
    parser.add_argument("--out", required=True, help="Output directory for the DVC stage (never data/raw/).")
    parser.add_argument(
        "--skip-dimension-check",
        action="store_true",
        help="Skip per-frame width/height verification (faster, less strict).",
    )
    args = parser.parse_args(argv)
    if not args.source:
        parser.error("--source is required (or set the CHOLECSEG8K_RAW_ZIP environment variable)")

    result = convert(
        args.source,
        args.out,
        verify_dimensions=not args.skip_dimension_check,
    )

    print(f"cholecseg8k convert: {len(result.instances['images'])} images, "
          f"{len(result.video_frame_counts)} videos, "
          f"annotations={result.annotations_status} ({len(result.instances['annotations'])} objects)")
    print(f"split totals: {json.dumps(result.split_frame_totals)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CATEGORIES",
    "ANNOTATIONS_BLOCKED_REASON",
    "EXPECTED_VIDEO_COUNT",
    "EXPECTED_FRAME_COUNT",
    "IMAGE_WIDTH",
    "IMAGE_HEIGHT",
    "FrameRecord",
    "patient_id",
    "iter_frames_from_zip",
    "iter_frames_from_dir",
    "validate_layout",
    "build_patient_split",
    "split_frame_counts",
    "assert_no_patient_leakage",
    "build_categories",
    "build_images",
    "build_annotations",
    "ConversionResult",
    "convert",
    "main",
]


