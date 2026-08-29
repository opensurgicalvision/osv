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
