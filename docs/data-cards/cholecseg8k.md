# Data Card: CholecSeg8k

**RESEARCH USE ONLY — NOT FOR CLINICAL USE**

Status: onboarded by `data-butler` per `osv/datasets/manifests/cholecseg8k.yaml`
(manifest reviewed and approved by the project owner, 2026-08-30). Semantic
segmentation annotations are **not yet generated** (Blocker #1 open — needs
authoritative human / Clinical Lead mapping, see §4a). Deterministic 4-layer
De-ID framework implemented and verified (PASS).

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
  but this specific dataset's NonCommercial clause was explicitly reviewed and
  accepted by the project owner as a condition of onboarding this dataset —
  see `docs/adr/0002-accepting-noncommercial-datasets.md` for the decision and
  what follows from it. Any downstream consumer of OSV that includes
  CholecSeg8k inherits the NC restriction for that portion of the benchmark.
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

### 4a. Segmentation annotations — generated, on a Clinical-Lead-approved mapping

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

Per this project's rule that an AI agent never defines anatomical classes (R-14),
an AI agent is **forbidden** from guessing this mapping or assigning anatomical
labels to raw mask clusters. `osv/datasets/cholecseg8k.py`'s `build_annotations`
strictly requires an explicit, human-supplied mapping (`pixel_to_category` or
`color_to_category`) and raises `NotImplementedError` without one.

**That mapping has since been sourced and signed off** — see the two
subsections below for the evidence and, importantly, the limits of the
sign-off. `instances.json` (the DVC-tracked pipeline output) now ships
`info.annotations_status: "generated"` with **95,928 polygon annotations**
over all 8,080 frames:

| id | class | objects | frames |
|---|---|---:|---:|
| 0 | Black Background | 13,685 | 8,055 |
| 1 | Abdominal Wall | 13,616 | 7,255 |
| 2 | Liver | 21,285 | 8,080 |
| 3 | Gastrointestinal Tract | 4,706 | 4,557 |
| 4 | Fat | 15,018 | 7,510 |
| 5 | Grasper | 8,562 | 6,020 |
| 6 | Connective Tissue | 2,914 | 1,600 |
| 7 | Blood | 2,696 | 692 |
| 8 | Cystic Duct | 244 | 241 |
| 9 | L-hook Electrocautery | 2,272 | 2,253 |
| 10 | Gallbladder | 10,297 | 6,861 |
| 11 | Hepatic Vein | 385 | 317 |
| 12 | Liver Ligament | 248 | 240 |

Two independent consistency signals in that table: Liver Ligament resolves to
exactly the **240 frames** the exhaustive `ws=5` scan found, and Liver appears
in 8,080 of 8,080 frames — which is what a cholecystectomy field should look
like. No class is empty; no annotation has non-positive area, a degenerate
bbox, or a polygon under 3 points.

**Severe class imbalance — plan for it.** Liver carries 21,285 objects,
Cystic Duct 244 and Hepatic Vein 385, i.e. roughly a 50:1 to 90:1 ratio.
An unweighted loss will effectively ignore the rare classes. Report per-class
metrics, never the macro average alone.

#### ⚠️ Three classes are not benchmarkable on this split — read before quoting any number

The rare classes are concentrated in single videos, and R-08 requires the
split to cut by video. The two facts together produce this:

| class | train | val | test | consequence |
|---|---:|---:|---:|---|
| Cystic Duct | 242 | 0 | **2** | test score computed on 2 objects — statistically meaningless |
| Hepatic Vein | **385** | 0 | **0** | in training data only; **cannot be evaluated at all** |
| Liver Ligament | **0** | 248 | **0** | never seen in training; **cannot be learned or tested** |

This is not a bug in the split code — the split is a correct whole-video
partition (train 12 / val 2 / test 3 videos). It is a property of the dataset
meeting R-08. And for Liver Ligament it is **not fixable by re-splitting**:
the class exists in exactly one video (`video09`), so no video-level
partition can place it in train *and* val *and* test at once. Putting it in
train would only move the hole, not close it.

Consequences to respect:

- Do **not** publish per-class IoU/Dice for Cystic Duct, Hepatic Vein or
  Liver Ligament from this split. Mark them `N/A — insufficient split
  coverage`, not `0.0`, and never fold them into a macro average, which would
  silently drag the headline number.
- A model trained here has **seen no Liver Ligament examples at all**. Any
  prediction it makes for that class is out-of-distribution behaviour.
- If those three classes matter for a research question, that needs either an
  additional data source or a documented k-fold / leave-one-video-out
  protocol over all 17 videos — a human decision, recorded in
  `docs/BENCHMARK.md`, not a quiet change to this split (an already-published
  split is frozen; changing it retroactively makes prior numbers
  incomparable).

#### Candidate mapping — mechanical evidence (established) 

Two independent community implementations publish complementary halves of
the encoding. Both were fetched and read directly (not taken second-hand):

- `github.com/mhjd/cholecseg8k-deeplabv3` → `src/masks.py`: `LABEL_MAP`,
  watershed grayscale value → class id, plus `IGNORE_INDEX = 255`.
- `github.com/dataset-ninja/cholec-seg8k` → `src/convert.py`:
  `class_to_color`, class name → RGB in `*_endo_color_mask.png`.

Because these are two *independent* encodings of the same annotation, their
mutual consistency is checkable mechanically, with no anatomical judgement
involved. Cross-check performed on 12 frames drawn from 6 different videos
(`scratchpad/crossval_mapping.py`): for each watershed value, the set of
pixels carrying it was compared against the RGB at those same pixels.

**Result: 13 of 13 classes co-locate at 100.0% purity.** Two corrections to
the community tables were found in the process:

| watershed | co-located RGB | class | note |
|---|---|---|---|
| 11 / 12 / 13 / 21 / 22 / 23 / 24 / 25 / 31 / 32 / 33 | as published | Abd. Wall, Fat, GI Tract, Liver, Gallbladder, Conn. Tissue, Blood, Cystic Duct, Grasper, L-hook, Hepatic Vein | exact match |
| 50 | `(127,127,127)` | Black Background | **not `(0,0,0)`** — the archive uses `#7F7F7F` |
| 5 | `(111,74,0)` | Liver Ligament | present in **video09 only**, 240 frames — see below |
| 255 | `(255,255,255)` | — | watershed boundary, not a class (`IGNORE_INDEX`) |

`ws = 5` was verified by an **exhaustive scan of all 8,080 masks**
(`scratchpad/find_ligament.py`), not a sample: it occurs in 240 frames, all
in `video09`, and all 240 co-locate with `(111,74,0)`. This confirms the
community claim that the class is rare enough to miss in random sampling.

What the above does **not** establish: that a given colour corresponds to a
given *anatomical structure*. Pixel-to-pixel agreement between two encodings
is a mechanical fact; "this region is the liver" is a clinical reading. That
half is R-14 territory and is recorded below.

#### Clinical Lead sign-off — SIGNED (scope-limited, see caveat)

Review material prepared for adjudication (raw frame │ colour mask │ overlay):

- `01_video01_frame_16638_endo.png` — 10 classes incl. Liver, Gallbladder,
  Cystic Duct, Blood, Grasper
- `02_video12_frame_19766_endo.png` — 10 classes incl. L-hook, Conn. Tissue
- `03_video12_frame_19553_endo.png` — 10 classes incl. Hepatic Vein
- `ws5_01_video09_frame_1031_endo.png` — the Liver Ligament candidate,
  isolated and outlined (73,145 px)

| Field | Value |
|---|---|
| Reviewer (name, role) | Egor Minsky — Clinical Lead (RC) |
| Date of review | 2026-09-01 |
| Frames reviewed | the four listed above (`01_`, `02_`, `03_`, `ws5_01_`) |
| Verdict | Mapping confirmed correct ("да, всё верно") |
| How recorded | Relayed by the project owner in the working session, not entered first-hand by the reviewer |

**Scope caveat — this sign-off covers a narrow sample, and a reader should
weight it accordingly.** The four frames were selected *by the agent*, on a
convenience criterion (maximum distinct classes per frame), not by the
reviewer and not at random. Concretely:

- They span **3 of the 17 videos** (`video01`, `video12`, `video09`);
  `02_` and `03_` are both from `video12`, ~213 frames apart — the same
  operative phase, lighting and patient, so they are far less independent
  than "three frames" suggests.
- Ranking by class-density structurally favours clean, well-lit, richly
  annotated frames and excludes the hard cases where a mapping error would
  show most: smoke, blood wash, motion blur, small regions, tissue borders.
- 11 of the 17 videos were never displayed at all.

What the sign-off therefore establishes: the colour↔structure reading is
correct **on legible, class-dense frames from three videos**. It is not a
stratified, per-class, all-video audit. A wider adversarial sample (per-class
frames from every video, including minimum-area and occluded instances)
remains available to run if a stronger claim is ever needed — e.g. before
publishing benchmark numbers that depend on rare-class accuracy.

Combined with the mechanical 13/13 colour↔value cross-check above (which is
exhaustive for `ws=5` and 100%-pure elsewhere), this is considered sufficient
to unblock annotation generation. `build_annotations` still requires the
mapping to be passed explicitly at the call site — the sign-off authorises a
value, it does not turn the guard off.


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

The 4-layer De-ID framework (`osv.deid`) is implemented:
- **Layer 1:** PS3.15 Annex E standard tag validation (DICOM).
- **Layer 2:** Private vendor tag scanning and stripping (odd groups).
- **Layer 3:** Deterministic morphological + OCR text candidate detection in pixel space.
- **Layer 4:** Volumetric 3D defacing indicator check (filename/metadata heuristic only; full geometric 3D mesh surface analysis scheduled for Phase 1 R3 3D track).


## 5. De-identification / PHI Audit Results

Ran `python -m osv.deid.scan` over sampled raw endoscopic frames:

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

Verdict: **PASS** — zero burned-in hospital names, timestamps, patient identifiers, or private tags found across inspected frames.


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
