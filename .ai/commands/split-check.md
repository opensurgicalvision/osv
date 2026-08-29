---
description: Verify a dataset split is partitioned by patient, not by frame
argument-hint: <dataset-name>
---

Audit the train/val/test split of `$ARGUMENTS` for leakage.

1. Resolve every sample to its patient / operation / session id.
2. Compute the intersection of id sets across all three splits. It must be empty.
3. Report per-split counts of patients, operations and frames, plus class balance.
4. Flag near-duplicates: consecutive frames of one operation landing in different splits.

Frame-level leakage produces metrics that look excellent and mean nothing. Treat any
non-empty intersection as a critical bug (R-08): open an issue, do not quietly "adjust" the split.

End with `SPLIT: CLEAN` or `SPLIT: LEAKAGE (<n> shared patients)`.
