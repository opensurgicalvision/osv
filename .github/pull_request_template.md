## Pull Request Description

### Related Issue
Closes #... / Fixes #...
> ⚠️ **ISSUE-FIRST POLICY:** Every PR must reference an open issue with approved assignment. PRs without assigned issues will be auto-labeled `invalid`.

### Summary of Changes
- ...

---

## Mandatory Quality & Safety Checklist

- [ ] **Zero PHI:** I confirm this PR contains NO unprotected patient health information, raw patient DICOMs, or un-scrubbed private tags.
- [ ] **Patient Splitting:** If modifying dataset loaders, I confirm that dataset splits are partitioned strictly by patient/operation (no inter-patient frame leakage).
- [ ] **DCO Sign-Off:** All commits include Developer Certificate of Origin (`git commit -s`).
- [ ] **AI-Tooling Sync:** If `.ai/` prompt/context files were modified, I ran `make setup-ai` (or `python .ai/build.py`) and verified with `make check-ai`.
- [ ] **Tests Pass:** `pytest` passes locally.
- [ ] **Linting:** `make lint` passes without errors.
