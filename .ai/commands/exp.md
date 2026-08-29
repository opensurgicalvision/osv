---
description: Turn an MLflow/W&B run into a report
argument-hint: <run-id>
---

Generate the experiment report for run `$ARGUMENTS` using the `experiment-report` skill.

Pull config, metrics, dataset version hash and commit hash through the `osv-experiments` MCP.
Include per-class metrics - a headline mIoU hides exactly the rare classes we care about - and
compare against the current golden baseline, flagging any regression above 0.5%.

Every number must come from the run record. If a value is missing, say it is missing;
never interpolate or estimate one (R-15).
