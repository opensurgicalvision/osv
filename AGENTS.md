# AGENTS.md — OpenSurgicalVision Autonomous AI Directives

<!-- AUTO-GENERATED from .ai/context.md DO NOT EDIT DIRECTLY -->

# OpenSurgicalVision AI Assistant Context

You are assisting developers, data scientists, and clinical researchers contributing to **OpenSurgicalVision (OSV)**  -  an open-source benchmark, dataset hub, and baseline model zoo for surgical computer vision and laparoscopic scene understanding.

---

## 1. Absolute Directives & Red Lines

1. **RESEARCH USE ONLY:** Every model card, README, user-facing prompt, API response, and visualization MUST prominently display: `RESEARCH USE ONLY  -  NOT FOR CLINICAL USE`.
2. **ZERO PHI / NO RAW PATIENT DATA:**
   - Never commit raw medical images, DICOMs, or patient metadata to git.
   - All data inputs must pass the 4-layer de-identification check (DICOM PS3.15, private tag stripping, OCR burned-in text detection, 3D defacing).
   - MCP servers must return ONLY derivatives, metrics, and metadata  -  NEVER raw pixels or private tags.
3. **CLINICAL LEAD AUTHORITY (RC):**
   - The Clinical Lead (RC) has absolute final authority on anatomical definitions, boundary ground-truth, and clinical relevance of metrics.
   - AI agents are strictly forbidden from approving Annotation Guidelines, resolving contested anatomical boundaries, or claiming clinical efficacy.
4. **PATIENT-LEVEL DATA SPLITS:**
   - All dataset splits MUST be partitioned strictly by patient/operation/session. Frame-level or slice-level random splits that mix patient data between train and test sets are considered critical bugs.
5. **DETERMINISTIC GATES OVER LLMs:**
   - Security, PHI detection, and PR triage must rely on deterministic rule-based checks first. LLMs may only summarize or draft, never serve as the sole gatekeeper for security or privacy.

---

## 2. AI Role Matrix (Boundaries of Automation)

| AI Allowed Completely | AI Drafts, Human Decides | AI Strictly Prohibited |
|---|---|---|
| Format converters, boilerplate, test harnesses | First-pass PR review comments | Defining anatomical classes |
| Markdown docs drafts, changelogs | Draft sections of scientific papers | Resolving contested boundary adjudications |
| MLflow/W&B metrics report generation | Backlog prioritization suggestions | Approving official Annotation Guidelines |
| arXiv/PubMed deadline monitoring | SAM 2 pre-annotation proposals | Declaring a model "clinically safe" |
| Issue triage and label classification | Model card descriptions | Modifying the core Clinical Disclaimer |

---

## 3. Code & Engineering Standards

- **Python:** 3.10+ with strict typing (`mypy`), formatted and linted with `ruff`.
- **Frameworks:** PyTorch, Albumentations, Hydra, FastAPI, DVC, Hatchling.
- **Reproducibility:** Fix random seeds, document package versions, log MLflow run hashes, store golden benchmark outputs.
- **AI Tooling:** The `.ai/` directory is the canonical source of truth for prompts, context, and MCP configurations. All IDE-specific files (`.claude/`, `.cursor/`, `.github/copilot-instructions.md`, `AGENTS.md`, `.aider.conf.yml`) are generated via `python .ai/build.py`.

---

# OSV Project Rules

**A rule that nothing checks is decoration.** Every rule below names its enforcement mechanism.
Rules marked 🔒 are mechanically blocked and cannot be bypassed by an agent, a hook flag, or a
persuasive prompt. Rules marked 👁 are advisory and rely on human review.

| # | Rule | Enforcement | Type |
|---|---|---|---|
| R-01 | No raw medical data (`*.dcm`, `*.nii`, `*.nii.gz`, `*.mha`, `*.mp4`, `*.avi`) enters git. Data lives in DVC only. | `phi_path_guard` hook + `pre-commit-phi-guard` + CI `test_no_data_in_git` | 🔒 |
| R-02 | No file may be written into `data/raw/` from an agent session. | `phi_path_guard` hook | 🔒 |
| R-03 | Every model card, README, Space, and API response carries `RESEARCH USE ONLY — NOT FOR CLINICAL USE`. | `disclaimer_guard` hook + `pre-publish-disclaimer` + CI | 🔒 |
| R-04 | Protected paths (`LICENSE*`, `docs/clinical-disclaimer.md`, `.github/workflows/`, `.ai/context.md`, `.ai/rules.md`) are never edited by an agent without an explicit human instruction naming the file. | `phi_path_guard` hook + CODEOWNERS | 🔒 |
| R-05 | Notebook outputs are stripped before write. Surgical frames rendered in `.ipynb` outputs are PHI. | `notebook_guard` hook + `nbstripout` in pre-commit | 🔒 |
| R-06 | `git commit --no-verify`, `--no-gpg-sign`, and force-push to `main` are forbidden. | `bash_guard` hook + branch protection | 🔒 |
| R-07 | Network egress from an agent session is allowlisted (GitHub, HF, arXiv, PubMed, PyPI). No `curl`/`wget` to arbitrary hosts. | `bash_guard` hook + CI egress policy | 🔒 |
| R-08 | Dataset splits are partitioned by patient / operation / session. Frame-level random splits are a critical bug. | CI `test_no_patient_leakage` + `/split-check` command | 🔒 |
| R-09 | Security, PHI, and PR-triage gates are deterministic. An LLM may summarize a verdict but never produce it. | Architecture (§5.11 of the plan); CI jobs carry no LLM secret | 🔒 |
| R-10 | No agent merges to `main`, closes a human's issue, or edits another contributor's PR branch. | GitHub `permissions:` scoping + branch protection | 🔒 |
| R-11 | `pull_request_target` with checkout of PR head is forbidden in any workflow. | `workflow-lint` CI job | 🔒 |
| R-12 | Secrets are never printed, echoed, interpolated into logs, or written to files. | `bash_guard` hook + secret scanning + log masking | 🔒 |
| R-13 | Generated AI configs stay in sync with `.ai/`. Editing `.claude/` directly is invalid. | `python .ai/build.py --check` in CI | 🔒 |
| R-14 | Anatomical class definitions, contested boundaries, Annotation Guideline changes, and any "clinically safe" claim require Clinical Lead (RC) sign-off. | Human process + CODEOWNERS on `docs/ANNOTATION_GUIDELINE.md` | 👁 |
| R-15 | Every numeric claim in a paper traces to an MLflow run id. No figure or number originates from model output. | `paper-section` skill contract + R0 review | 👁 |
| R-16 | Every citation is verified against arXiv/PubMed before it enters a draft. | `paper-section` skill + MCP lookup | 👁 |
| R-17 | VLM mask audit reports semantic errors only. It never scores geometry. | `annotation-qc` skill contract + review | 👁 |
| R-18 | AI-generated code carries the same DCO sign-off; the human signing is responsible for provenance. | DCO check + review | 👁 |
| R-19 | A PR without a linked issue that has a requested assignment is closed automatically. Labels `pre-approved` / `trivial` exempt it. | `pr-triage` deterministic rule | 🔒 |
| R-20 | Pre-annotation control frames (10%, unmarked) are never disabled, and acceptance-rate telemetry is never suppressed. | `bias-watchdog` agent + CI check on annotation config | 🔒 |

## Escalation

If a rule blocks legitimate work, the fix is to change the rule through a PR against `.ai/rules.md`
with R1 approval (plus R0 for R-03, R-04, R-09, R-14). The fix is never a local bypass, a
`--force`, or a disabled hook.

## Registered OSV Skills

### `annotation-qc`

# Skill: annotation-qc
**Priority:** P0 | **Owner:** R5 | **Scope:** Annotation Quality Assurance

## Purpose
Calculates inter-rater agreement statistics and detects defective annotations.

## Tasks
1. Compute Fleiss kappa across multiple clinical raters (target >= 0.70).
2. Compute mean pairwise Dice and IoU matrices.
3. Detect "lazy masks" (bounding-box polygons, unrefined coarse hulls).
4. Identify duplicate or near-duplicate frames.
5. Export quality control dashboard summary.

---

### `bias-report`

# Skill: bias-report
**Priority:** P0 | **Owner:** R5 | **Scope:** Annotation & AI Alignment

## Purpose
Generates periodic automation bias audit reports evaluating whether annotators blindly accept SAM 2 suggestions.

## Key Metrics
1. **Delta-Contour Dice:** Compare pre-annotated frames against blind control frames (target >= 0.90).
2. **Acceptance Rate:** Track percentage of unedited AI suggestions (target < 60%).
3. **Class Area Drift:** Detect systematic boundary shrink/inflation per anatomical class.
4. If a class violates thresholds, recommend disabling SAM 2 pre-annotation for that specific class.

---

### `cfp-abstract`

# Skill: cfp-abstract
**Priority:** P1 | **Owner:** R7 | **Scope:** Conference Submissions

## Purpose
Generates structured paper abstracts satisfying strict word count, clinical motivation, methodological novelty, and benchmark results for conferences (IPCAI, MIDL, MICCAI, CARS, ISBI).

---

### `clinical-review-pack`

# Skill: clinical-review-pack
**Priority:** P0 | **Owner:** R5 | **Scope:** Clinical Lead Efficiency

## Purpose
Prepares a structured review package for the Clinical Lead (RC) to maximize the utility of their limited time (2 hrs/week).

## Structure
1. Extract disputed frames flagged as `needs-clinician`.
2. Provide cropped context images with candidate boundary overlays.
3. Formulate precise, closed-ended anatomical questions.
4. Reference current `ANNOTATION_GUIDELINE.md` clauses.
5. Provide a template for recording the final ruling into `docs/adjudications.md`.

---

### `data-card`

# Skill: data-card
**Priority:** P0 | **Owner:** R5 | **Scope:** Data Documentation

## Purpose
Generates a complete Data Card adhering to the Datasheets for Datasets standard for a dataset in `osv/datasets/`.

## Sections to Populate
1. **Dataset Origin:** Original authors, institution, year, publication DOI.
2. **License & Restrictions:** Commercial/non-commercial, attribution, distribution rights.
3. **Clinical Domain:** Modality (laparoscopy, endoscopy, CT), procedure type, anatomical structures.
4. **De-identification Status:** Results of `deid-audit`, confirmation of zero PHI.
5. **Known Biases:** Camera models, illumination settings, patient demographic limits.
6. **Patient Splits:** Document patient IDs per split and verify zero cross-contamination.

---

### `dataset-onboard`

# Skill: dataset-onboard
**Priority:** P0 | **Owner:** R4 | **Scope:** Data Aggregation

## Purpose
Automates the full cycle of onboarding an open surgical dataset into OpenSurgicalVision.

## Workflow
1. Download dataset using official public scripts or URL.
2. Verify checksums against `docs/data-cards/licenses.md`.
3. Run 4-layer de-identification check (`osv.deid.verify_no_phi`).
4. Generate strictly patient-isolated splits (train/val/test).
5. Implement converter to standard COCO (2D) or NIfTI (3D) in `osv/datasets/`.
6. Add unit test `test_no_patient_leakage()` in `tests/`.
7. Generate template Data Card in `docs/data-cards/<dataset_name>.md`.

---

### `deid-audit`

# Skill: deid-audit
**Priority:** P0 | **Owner:** R4 | **Scope:** Data Safety & PHI Defense

## Purpose
Executes comprehensive 4-layer de-identification verification on any dataset candidate.

## Protocol
1. Scan DICOM headers for PS3.15 standard compliance.
2. Flag and scrub all odd-numbered private vendor tags.
3. Perform OCR inspection over every frame to detect burned-in ultrasound/CT text or patient names.
4. Check 3D facial surface meshes and apply defacing if skull features are present.
5. Generate an audit report markdown detailing findings and zero-PHI verification status.

---

### `experiment-report`

# Skill: experiment-report
**Priority:** P1 | **Owner:** R4 | **Scope:** ML Tracking & Reporting

## Purpose
Fetches MLflow / W&B run artifacts and compiles an experiment report with metrics, parameter comparisons, and loss curves. Never hallucinate numbers — cite specific run IDs and commit hashes.

---

### `good-first-issue`

# Skill: good-first-issue
**Priority:** P1 | **Owner:** R8 | **Scope:** Community Onboarding

## Purpose
Transforms an unrefined backlog idea or task into an accessible, structured `good first issue` for external open-source contributors.

## Structure
1. Context & goal of the task.
2. Expected behavior and files to modify.
3. Step-by-step instructions to test locally.
4. Definition of Done.
5. Primary mentor handle for questions.

---

### `model-card`

# Skill: model-card
**Priority:** P0 | **Owner:** R2 | **Scope:** Model Releases

## Purpose
Generates official model documentation for Hugging Face Hub releases.

## Mandatory Elements
1. Top-level disclaimer banner: `RESEARCH USE ONLY — NOT FOR CLINICAL USE`.
2. Architecture details, parameter counts, and backbone weights.
3. Training dataset list and strict inheritance of most restrictive dataset license.
4. Quantitative benchmarks: mIoU, Dice, inference latency p50/p95 on RTX 4090 / Jetson AGX Orin.
5. Robustness evaluation across smoke levels, blood splatter, and defocus.

---

### `paper-section`

# Skill: paper-section
**Priority:** P1 | **Owner:** R1 | **Scope:** Academic Publications

## Purpose
Drafts a section of a scientific paper in LaTeX format tailored to target conference guidelines (MICCAI, IPCAI, MIDL).
All metrics must link to real MLflow experiment run IDs.
All external citations must be verified via PubMed/arXiv MCP servers.
Includes mandatory Ethics & Limitations subsections.

---

### `release-notes`

# Skill: release-notes
**Priority:** P1 | **Owner:** R7 | **Scope:** Releases & Community Updates

## Purpose
Generates release notes from merged pull requests, highlights breaking changes, new models, and contributors, and prepares distribution drafts for GitHub Releases, Hugging Face, and community channels.

---

### `repro-check`

# Skill: repro-check
**Priority:** P1 | **Owner:** R5 | **Scope:** Reproducibility Verification

## Purpose
Performs end-to-end verification of model training from a clean repository clone:
1. Clones repository into isolated container.
2. Ingests data using automated downloaders.
3. Executes training pipeline with deterministic seed.
4. Computes metric diff with declared golden metrics (must match within +-0.3%).

---

### `social-post`

# Skill: social-post
**Priority:** P2 | **Owner:** R7 | **Scope:** External Communications

## Purpose
Prepares concise, technically accurate social media updates (LinkedIn, X/Twitter, Habr, Medium) following the OpenSurgicalVision brand guidelines.
Ensures zero unsubstantiated clinical claims and validates that only fully de-identified synthetic/open images are shown.

---

## Registered OSV Agents

Full definitions (tools, triggers, hard boundaries) live in `.ai/agents/*.md` and `.claude/agents/*.md` for Claude Code specifically. Summary:

| Agent | Role |
|---|---|
| `bias-watchdog` | Weekly automation-bias evaluator for SAM 2 pre-annotation. Computes delta-contour, acceptance rate, and per-class systematic drift from control frames, then recommends (never applies) disabling pre-annotation for the affected class. Use PROACTIVELY after any annotation batch closes, or on demand via /bias. |
| `cfp-scout` | Tracks conference-deadline calendar (IPCAI, MIDL, MICCAI, ISBI, CARS, Hamlyn, SPIE, NeurIPS D&B, EMBC, SAGES/EAES, CVPR/ICCV workshops) and opens a reminder issue 8 weeks out per venue, per the plan's own submission-prep rule. Drafts, never submits. Use PROACTIVELY on schedule. |
| `content-drafter` | Drafts release notes, blog posts, and social copy from merged PRs and releases, per the content calendar. Never publishes externally and never claims clinical validation or parity with commercial systems. Use PROACTIVELY on release, or when a content-plan slot comes due. |
| `dataset-scout` | Biweekly scan for newly published open surgical-vision datasets. Drafts an onboarding issue with a licence read; never downloads, converts, or commits data itself. Use PROACTIVELY on schedule or when asked to find new datasets. |
| `deid-gate` | Reads the output of the deterministic de-identification scan and turns it into a readable PR comment. Use PROACTIVELY whenever a PR touches osv/datasets/, osv/deid/, dvc.yaml, or anything under data/. Never the source of truth on PASS/FAIL - that verdict is produced by a separate, secret-free script before this agent ever runs. |
| `literature-digest` | Weekly digest of new surgical-AI preprints relevant to the benchmark (MICCAI, IPCAI, MIDL, ISBI, CARS and adjacent venues). Flags relevance, never asserts a verdict on our own work. Use PROACTIVELY on schedule. |
| `newcomer-greeter` | Welcomes a contributor's first PR or issue with onboarding pointers. Use PROACTIVELY when GitHub reports a first-time-contributor event. Purely social - pr-triage owns the technical review. |
| `pr-triage` | First responder for every pull request. Runs a structured first-pass review (style, tests, rules compliance) and enforces the issue-linkage rule that keeps AI-slop PRs from burying maintainers. Use PROACTIVELY on every opened or updated PR. Holds no merge rights and never touches PR code itself. |
| `repro-nightly` | Nightly clean-clone reproducibility check against published benchmark numbers, tolerance +/-0.3%. Opens an issue with the environment diff on failure. Use PROACTIVELY on the nightly schedule. |
