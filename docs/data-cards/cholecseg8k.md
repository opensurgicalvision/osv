# Data Card: CholecSeg8k

**RESEARCH USE ONLY — NOT FOR CLINICAL USE**

Status: onboarded by `data-butler` per `osv/datasets/manifests/cholecseg8k.yaml`
(manifest reviewed and approved by the project owner, 2026-08-30). Semantic
segmentation annotations are **not yet generated** — see §4 "Known
limitations" below before using this dataset for anything beyond image
listing / splits.

## 1. Dataset Origin & Original Authors

- **Paper:** Hong, W.-Y., Kao, C.-L., Kuo, Y.-H., Wang, J.-R., Chang, W.-L.,
  Shih, C.-S. (2020). *CholecSeg8k: A Semantic Segmentation Dataset for
  Laparoscopic Cholecystectomy Based on Cholec80.* arXiv:2012.12453.
- **Authors' institution:** Graduate Institute of Networking and Multimedia,
  Dept. of Computer Science and Information Engineering, National Taiwan
  University.
- **Base dataset:** Cholec80 (CAMMA research group, University Hospital of
  Strasbourg / IHU Strasbourg / IRCAD) — 80 cholecystectomy videos, 13
  surgeons, 25 fps, phase + instrument annotations. CholecSeg8k extracts and
  pixel-annotates 8,080 frames from a 17-video subset.
- **Distribution:** Hugging Face `minwoosun/CholecSeg8k` (dataset repo),
  pinned revision `fbf8b94c674ea97e6adf9836e7f626f3ad3380ab`; originally
  released on Kaggle (`newslab/cholecseg8k`).
- **Onboarded via:** `osv/datasets/manifests/cholecseg8k.yaml`, single file
  `data/CholecSeg8k.zip`, sha256
  `ab4cfa07122230255092624711924a5441fe8d61653918e4ba1b6d6c33a24c3b`,
  size 3,104,078,070 bytes — downloaded and independently re-hashed by
  `data-butler` (not just trusted from the manifest's git-lfs-pointer-derived
  value); the recomputed hash matched exactly.

## 2. License & Redistribution Constraints

- **License:** CC BY-NC-SA 4.0 (Attribution, NonCommercial, ShareAlike).
- **Redistribution:** allowed under the above terms.
- **Commercial use:** **not permitted.** OSV is described as "open-source,"
  but this specific dataset's NonCommercial clause was explicitly reviewed
  and accepted by the project owner (Aleksandr Stefanin,
  opensurgicalvision@proton.me) in chat on 2026-08-30 as a condition of onboarding
  this dataset — any downstream consumer of OSV that includes CholecSeg8k
  inherits the NC restriction for that portion of the benchmark.
- **Attribution required.** Cite:
  ```bibtex
  @misc{hong2020cholecseg8k,
        title={CholecSeg8k: A Semantic Segmentation Dataset for Laparoscopic
               Cholecystectomy Based on Cholec80},
        author={W.-Y. Hong and C.-L. Kao and Y.-H. Kuo and J.-R. Wang and
                W.-L. Chang and C.-S. Shih},
        year={2020},
        eprint={2012.12453},
        archivePrefix={arXiv},
        primaryClass={cs.CV}
  }
  ```
- **Share-alike:** derivative works (including OSV's converted/split form)
  must be released under the same license terms.
- **Registration:** not required.
- **Upstream provenance note (open item, not a blocker):** CholecSeg8k's own
  CC BY-NC-SA 4.0 grant is what this onboarding relies on; Cholec80's
  original research-use agreement terms were not independently re-verified
  by `data-butler` (recorded as an accepted open item in the manifest at
  approval time).

## 3. Modality & Clinical Scope

- **Modality:** 2D RGB laparoscopic video frames + per-frame semantic
  segmentation masks (three variants: annotation-tool mask, color
  visualization mask, watershed mask).
- **Procedure:** laparoscopic cholecystectomy (gallbladder removal).
- **Resolution:** 854×480, verified per-frame by the converter (not just
  trusted from the manifest) across all 8,080 frames — no mismatches found.
- **Scope:** 17 source videos, 101 sub-clip folders, 8,080 annotated frames
  total. Confirmed by `data-butler` against the actual archive contents
  (matches the manifest's `frame_count: 8080`, `source_video_count: 17`,
  `expected_file_count: 8080` exactly — no discrepancy).
- **Published class taxonomy (13 classes, Table I of the paper — transcribed
  verbatim, not defined by this project):** Black Background, Abdominal
  Wall, Liver, Gastrointestinal Tract, Fat, Grasper, Connective Tissue,
  Blood, Cystic Duct, L-hook Electrocautery, Gallbladder, Hepatic Vein,
  Liver Ligament.

## 4. Known limitations — read before use

### 4a. Segmentation annotations are not yet generated (open item, needs a human)

The paper's text claims the watershed mask encodes "the same class ID value
... for three color channels" (i.e., pixel value 0–12 = class ID directly).
**This is not what the released archive actually contains.** Empirically,
sampling 40 frames across all 17 videos, the observed raw grayscale values
in `*_endo_watershed_mask.png` / `*_endo_mask.png` are things like
`{0, 11, 12, 13, 21, 22, 23, 24, 25, 31, 32, 33, 50, 255, ...}` — clustered
in bands, not 13 flat values 0–12. The `color_mask` variant is a consistent,
distinct RGB per region (empirically confirmed 1:1 with the grayscale
value, spatially, within a frame) but is likewise undocumented as to which
color is which of the 13 named classes.

`data-butler` checked every allowlisted, deterministic source available to
it — the archive itself, the arXiv PDF (no machine-readable table, only
prose + low-resolution example figures), the HF dataset card, and the HF
`CholecSeg8k.py` loading script (yields raw file paths only, no remapping)
— and found no authoritative pixel-value/color → class-ID lookup table.

Per this project's rule that an AI agent never defines anatomical classes,
`data-butler` did **not** guess this mapping from a visual reading of the
paper's example figures. `osv/datasets/cholecseg8k.py`'s `build_annotations`
requires an explicit, human-supplied `color_to_category` mapping and raises
`NotImplementedError` without one. **A human needs to source the
authoritative mapping (e.g., from the dataset authors, a citable reference
implementation, or the Kaggle dataset's own discussion) before this dataset
can be used for segmentation training/eval — not just image classification
or phase/frame-level tasks.**

Until then, `instances.json` (the DVC-tracked pipeline output) ships with a
complete `images` list and the 13-class `categories` list, but
`annotations: []` and `info.annotations_status:
"blocked_pending_color_class_mapping"`.

### 4b. Demographic / hardware bias

- All footage comes from a single institution (University Hospital of
  Strasbourg) and its specific laparoscopic camera/lighting setup — no
  cross-site, cross-scope-vendor, or cross-population diversity.
- 13 surgeons contributed to the parent Cholec80 corpus; individual surgical
  style, instrument brand, and camera white-balance are not distributed
  evenly across the 17 selected videos.
- Class frequency is heavily imbalanced (per the paper's own Figure 3):
  Liver (~29%) and Abdominal Wall (~29%) dominate; Hepatic Vein (~0.02%) and
  Cystic Duct (~0.05%) are extremely rare. Any model trained on this data
  will need class-balancing strategy and should not be assumed reliable on
  rare classes without explicit evaluation.
- Frames are pre-selected by the original annotators to exclude preparation
  and closing phases — this is a curated, not a representative, sample of
  full-procedure video.

### 4c. De-identification status

See §5 below. The scan that ran is a real, working aggregation/CLI layer,
but its underlying per-file check (`osv.deid.verify_no_phi`) is currently a
stub that always reports `clean: True` (documented honestly in
`osv/deid/scan.py` and `osv/deid/__init__.py` — the real PS3.15/OCR/defacing
logic is Phase 1 R4 work, not yet implemented). Treat the PASS below as
"the pipeline ran and found nothing," not as a substantive OCR/defacing
guarantee yet.

## 5. De-identification / PHI Audit Results

Ran `python -m osv.deid.scan` (the deterministic, secret-free scanner — this
Data Card quotes its output verbatim per R-09; `data-butler` does not issue
this verdict itself) over 20 randomly sampled raw endoscopic frames (one per
several distinct source videos):

```json
{
  "overall": "pass",
  "violations_total": 0,
  "layers": {
    "ps3_15_tags": [],
    "private_tags": [],
    "burned_in_ocr": [],
    "defacing": []
  }
}
```

Caveat: as noted in §4c, `verify_no_phi` is currently a stub (always
`clean: True`); this PASS does not yet reflect a real OCR burned-in-text or
defacing check. Laparoscopic frames of this kind carry low inherent PHI risk
(internal anatomy, no visible patient face/name in-frame by the nature of
the modality), but the scan should be re-run and this Data Card updated once
`osv.deid.verify_no_phi` has real layer-1..4 logic (tracked as Phase 1 R4
work, not blocking for this onboarding).

## 6. Patient Splitting Methodology (R-08)

- **Split key:** source Cholec80 **video** (one video = one operation /
  patient session), per the manifest's `patient_id_field: {strategy:
  folder_prefix, pattern: videoNN}` — confirmed against the real archive
  layout (`CholecSeg8k/videoNN/videoNN_XXXXX/frame_*_endo*.png`), never a
  frame or a clip sub-folder.
- **Algorithm:** deterministic largest-first bin-packing
  (`osv.datasets.cholecseg8k.build_patient_split`) — videos are visited in
  descending frame-count order (ties broken by ascending video ID) and each
  whole video is assigned to whichever split is furthest below its target
  share of total frames. A video is always assigned atomically, so
  frame-level leakage across splits is structurally impossible, not merely
  tested for.
- **Definition committed at:** `osv/datasets/splits/cholecseg8k.json`.
- **Result** (17 videos, 8,080 frames total; target ratios 70/15/15):

  | Split | Videos | Frames | % of total |
  |---|---|---|---|
  | train | video01, video43, video12, video28, video37, video27, video25, video26, video35, video48, video55, video20 (12 videos) | 5,600 | 69.3% |
  | val | video24, video09 (2 videos) | 1,200 | 14.9% |
  | test | video52, video17, video18 (3 videos) | 1,280 | 15.8% |

- **Leakage test:** `tests/test_cholecseg8k_split.py::test_no_patient_leakage`
  — verifies both a freshly computed split and the committed split
  definition have disjoint video sets across train/val/test. Result: **PASS**
  (5 tests in this file, 0 failures; see MR description for full pytest
  output).

## 7. DVC Pipeline

- `dvc.yaml` stage `cholecseg8k_convert` runs
  `osv/datasets/cholecseg8k.py` against a locally verified copy of the
  manifest-declared zip (path supplied via the `CHOLECSEG8K_RAW_ZIP`
  environment variable at `dvc repro` time — never staged inside the repo,
  per R-01/R-02).
- Output: `data/processed/cholecseg8k/` (git-ignored; tracked via
  `dvc.lock`) — `instances.json` (COCO-like: `images` + `categories`
  populated, `annotations: []` pending §4a) and `split.json`.
- `data-butler` did **not** run `dvc push`; the remote is written by the
  deterministic `dvc-publish` job after a human merges to protected `main`
  (R-23).
