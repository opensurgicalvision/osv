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
| R-04 | Protected paths (`LICENSE*`, `docs/clinical-disclaimer.md`, `.github/workflows/`, `.github/CODEOWNERS`, `.ai/context.md`, `.ai/rules.md`) are never edited by an agent without an explicit human instruction naming the file. | `phi_path_guard` hook + CODEOWNERS | 🔒 |
| R-05 | Notebook outputs are stripped before write. Surgical frames rendered in `.ipynb` outputs are PHI. | `notebook_guard` hook + `nbstripout` in pre-commit | 🔒 |
| R-06 | `git commit --no-verify`, `--no-gpg-sign`, and force-push to `main` are forbidden. | `bash_guard` hook + branch protection | 🔒 |
| R-07 | Network egress from an agent session is allowlisted (GitHub, HF, arXiv, PubMed, PyPI, npm registry, RunPod MCP, RunPod SSH). No `curl`/`wget`/`ssh`/`scp` to arbitrary hosts. | `bash_guard` hook + CI egress policy | 🔒 |
| R-08 | Dataset splits are partitioned by patient / operation / session. Frame-level random splits are a critical bug. | CI `test_no_patient_leakage` + `/split-check` command | 🔒 |
| R-09 | Security, PHI, and PR-triage gates are deterministic. An LLM may summarize a verdict but never produce it. | Architecture (§5.11 of the plan); CI jobs carry no LLM secret | 🔒 |
| R-10 | No agent merges to `main`, closes a human's issue, or edits another contributor's PR branch. | GitHub Actions `permissions:` scoping + a fine-grained token without `contents: write`; branch protection | 🔒 |
| R-11 | Stage B never checks out a PR's head. Secrets are only ever available to a workflow running in the trusted base-repo context, never to one triggered by the PR itself. | Two-stage `workflow_run` design (§5.11) + `workflow-lint` CI job | 🔒 |
| R-12 | Secrets are never printed, echoed, interpolated into logs, or written to files. | `bash_guard` hook + secret scanning + log masking | 🔒 |
| R-13 | Generated AI configs stay in sync with `.ai/`. Editing `.claude/` directly is invalid. | `python .ai/build.py --check` in CI | 🔒 |
| R-14 | Anatomical class definitions, contested boundaries, Annotation Guideline changes, and any "clinically safe" claim require Clinical Lead (RC) sign-off. | Human process + CODEOWNERS on `docs/ANNOTATION_GUIDELINE.md` | 👁 |
| R-15 | Every numeric claim in a paper traces to an MLflow run id. No figure or number originates from model output. | `paper-section` skill contract + R0 review | 👁 |
| R-16 | Every citation is verified against arXiv/PubMed before it enters a draft. | `paper-section` skill + MCP lookup | 👁 |
| R-17 | VLM mask audit reports semantic errors only. It never scores geometry. | `annotation-qc` skill contract + review | 👁 |
| R-18 | AI-generated code carries the same DCO sign-off; the human signing is responsible for provenance. | DCO check + review | 👁 |
| R-19 | A PR without a linked issue that has a requested assignment is blocked automatically. Labels `pre-approved` / `trivial` exempt it. | deterministic issue-link step in `.github/workflows/pr-triage.yml` — **the linkage half only; the "requested assignment" half is not yet checked, see the note below** | 🔒 |
| R-20 | Pre-annotation control frames (10%, unmarked) are never disabled, and acceptance-rate telemetry is never suppressed. | `bias-watchdog` agent + CI check on annotation config | 🔒 |
| R-21 | Agents that read untrusted PR content (`deid-gate`, `pr-triage`, `newcomer-greeter`) never hold the `Bash` tool. GitHub interaction goes through narrow, typed MCP tools only (`osv-github-ro` / `osv-github-triage`). | `python .ai/build.py --check` (`check_no_bash_for_restricted_agents`) | 🔒 |
| R-22 | Every agent's `model:` field is a literal ID present in `.ai/models.json`, never a floating tier alias (`sonnet`, `latest`). Approving or bumping a model is a reviewed PR against that file. | `python .ai/build.py --check` (`check_model_pins`) | 🔒 |
| R-23 | A research agent creates no data file outside a DVC stage, downloads only from a URL declared in a reviewed manifest with a verified checksum, and never runs `dvc push`. The PR carries text only (`*.dvc`, `dvc.lock`, manifest, converter, Data Card); the remote is written by the deterministic `dvc-publish` job after a human merge to protected `main`. | `phi_path_guard` hook + `permissions.ask` on `dvc push` + agent CI token without remote write + manifest checksum check in CI | 🔒 |
| R-24 | Every research agent runs under a weekly GPU-hour quota. Exhaustion is a normal exit with state preserved, not a lost run: finished seeds stay `FINISHED` in MLflow, an interrupted seed resumes from its checkpoint, an unfinished hypothesis outranks a new one, and a changed `config_hash` forbids resumption. | `scripts/check_compute_quota.py` before every run + MLflow child-run status + `config_hash` comparison + spend anomaly alert | 🔒 |
| R-25 | The held-out test set is a separate DVC track in a separate bucket, and the CI token issued to `arch-runner` has no read permission on it at the IAM level. An improvement is declared only on >= 3 finished seeds with non-overlapping confidence intervals; an incomplete series is marked `INCOMPLETE`. The search space is widened only by a human PR to `osv/arch/registry.py`. | IAM policy (403, not an instruction) + separate `heldout` DVC remote + `check_experiment_card.py` in CI + test-access counter in `docs/BENCHMARK.md` | 🔒 |
| R-26 | A demo clip is rendered only from frames listed in `demo-assets/allowlist.yaml`, carries a burned-in run id and the `RESEARCH USE ONLY - NOT FOR CLINICAL USE` notice, is stored as a tracker artifact or release asset and never in git, appears in a PR only as a markdown link, and is published outward only by a human. The allowlist itself is never edited from an agent session. | `demo_guard` hook + `disclaimer_guard` + `permissions.ask` on `hf upload` + allowlist check in CI | 🔒 |

## Known enforcement gap (R-19)

The workflow step behind R-19 checks only that the PR body references an issue
(`Fixes #123`). It does not check that the issue exists, is open, or that the author
requested assignment on it — so the second half of the rule as written is currently
enforced by nobody. By this document's own opening line that half is decoration until
the check is extracted into a deterministic, unit-tested script. Tracked as work, not
as a reason to soften the rule.

## Escalation

If a rule blocks legitimate work, the fix is to change the rule through a PR against `.ai/rules.md`
with R1 approval (plus R0 for R-03, R-04, R-09, R-14, R-26). The fix is never a local bypass, a
`--force`, or a disabled hook.

## Autonomous Agents in CI
The following agents operate asynchronously on this repository. Do not duplicate their work:

- **arch-runner**: Runs architecture experiments inside a declared search space and a hard weekly GPU quota - config from osv/arch/registry.py, at least 3 seeds, resumable state in MLflow, experiment card with confidence intervals. Never sees the held-out test set, never widens the search space, never calls an improvement significant on an incomplete series. Use PROACTIVELY when an architecture hypothesis issue is opened or /arch is invoked.
- **bias-watchdog**: Weekly automation-bias evaluator for SAM 2 pre-annotation. Computes delta-contour, acceptance rate, and per-class systematic drift from control frames, then recommends (never applies) disabling pre-annotation for the affected class. Use PROACTIVELY after any annotation batch closes, or on demand via /bias.
- **cfp-scout**: Tracks conference-deadline calendar (IPCAI, MIDL, MICCAI, ISBI, CARS, Hamlyn, SPIE, NeurIPS D&B, EMBC, SAGES/EAES, CVPR/ICCV workshops) and opens a reminder issue 8 weeks out per venue, per the plan's own submission-prep rule. Drafts, never submits. Use PROACTIVELY on schedule.
- **content-drafter**: Drafts release notes, blog posts, and social copy from merged PRs and releases, per the content calendar. Never publishes externally and never claims clinical validation or parity with commercial systems. Use PROACTIVELY on release, or when a content-plan slot comes due.
- **data-butler**: Takes an open dataset from a reviewed manifest to a patient-level split - download by declared URL, checksum verification, deterministic conversion, DVC stage, Data Card draft. Never writes a byte of data into git, never touches data/raw/, never runs `dvc push` and never issues the de-identification verdict. Use PROACTIVELY when an onboarding issue is opened or /dataset-add is invoked.
- **dataset-scout**: Biweekly scan for newly published open surgical-vision datasets. Drafts an onboarding issue with a licence read; never downloads, converts, or commits data itself. Use PROACTIVELY on schedule or when asked to find new datasets.
- **deid-gate**: Reads the output of the deterministic de-identification scan and turns it into a readable PR comment. Use PROACTIVELY whenever a PR touches osv/datasets/, osv/deid/, dvc.yaml, or anything under data/. Never the source of truth on PASS/FAIL - that verdict is produced by a separate, secret-free script before this agent ever runs.
- **demo-recorder**: Renders a 20-40 second clip after every finished run - prediction overlay, baseline versus candidate, burned-in run id and RESEARCH USE ONLY disclaimer - stores it as a tracker artifact and links it from the experiment card. Frames come only from demo-assets/allowlist.yaml; the clip never enters git and is never published outward by the agent. Use PROACTIVELY when a training run reaches FINISHED.
- **literature-digest**: Weekly digest of new surgical-AI preprints relevant to the benchmark (MICCAI, IPCAI, MIDL, ISBI, CARS and adjacent venues). Flags relevance, never asserts a verdict on our own work. Use PROACTIVELY on schedule.
- **newcomer-greeter**: Welcomes a contributor's first PR or issue with onboarding pointers. Use PROACTIVELY when GitHub reports a first-time-contributor event. Purely social - pr-triage owns the technical review.
- **pr-triage**: First responder for every pull request. Runs a structured first-pass review (style, tests, rules compliance) and enforces the issue-linkage rule that keeps AI-slop PRs from burying maintainers. Use PROACTIVELY on every opened or updated PR. Holds no merge rights and never touches PR code itself.
- **repro-nightly**: Nightly clean-clone reproducibility check against published benchmark numbers, tolerance +/-0.3%. Opens an issue with the environment diff on failure. Use PROACTIVELY on the nightly schedule.
