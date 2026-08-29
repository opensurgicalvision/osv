---
description: Onboard a new open dataset end to end
argument-hint: <dataset-name>
---

Onboard `$ARGUMENTS` using the `dataset-onboard` skill.

Order matters - stop at the first failure:

1. **Licence audit first.** Redistribution allowed? Commercial use? Registration required?
   If redistribution is forbidden we ship a download script plus checksums, never the data.
2. Loader and converter into the canonical format, registered in `osv.datasets`.
3. Patient-level splits, committed and DVC-versioned.
4. Tests: schema, checksums, `test_no_patient_leakage`.
5. Run `/deid` over a sample before anything is published.
6. Data Card with provenance, licence, ethical status, known biases, de-identification report.

Never write into `data/raw/` (R-02).
