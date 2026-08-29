---
description: Reproducibility check from a clean clone
argument-hint: <model-or-benchmark>
---

Run the reproducibility check for `$ARGUMENTS` using the `repro-check` skill.

Clean clone, documented command, compare against published metrics. Tolerance +/-0.3%.

Report the environment that produced any delta - package versions, CUDA, GPU model, seed -
because "works on my machine" is the failure mode this check exists to catch.

End with `REPRO: PASS` or `REPRO: FAIL (metric, expected, actual)`.
