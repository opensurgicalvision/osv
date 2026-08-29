---
description: Inter-rater agreement report for an annotation batch
argument-hint: <dataset-or-batch>
---

Produce the annotation QC report for `$ARGUMENTS` using the `annotation-qc` skill.

Include Fleiss/Cohen kappa for categorical decisions, mean pairwise Dice and IoU for masks,
and a per-assessor breakdown. Thresholds: kappa >= 0.70, mean pairwise Dice >= 0.80.

Below threshold means one of two things, and you must state that you cannot distinguish them:
the guideline is unclear, or the boundary is genuinely contested. The second is a question for
the Clinical Lead - assemble it with `/clinical` rather than guessing.

Report geometry only through these metrics. A VLM opinion on boundary quality is not evidence (R-17).
