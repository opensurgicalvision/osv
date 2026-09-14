---
description: Run one architecture experiment under the sandbox protocol
argument-hint: <hypothesis-or-issue-id>
---

Run the architecture hypothesis in `$ARGUMENTS` using the `arch-experiment` skill.

Before anything else, check the weekly GPU quota. If it is spent, stop and report
`ARCH: QUOTA EXCEEDED` with the saved state - do not start a run "just to see".

Then, in order:

1. **Config** - build it from `osv/arch/registry.py` only. A hypothesis needing an unregistered
   block stops here and reports what PR would unblock it.
2. **Resume, do not restart** - read the parent MLflow run, take the first seed that is not
   `FINISHED`, and verify `config_hash` matches. A changed config is a new hypothesis.
3. **Run >= 3 seeds** on the frozen patient-level split, same budget as the baseline. Validation
   only: the held-out test set is not reachable from here and must not be sought.
4. **Ablation** for any block being proposed for the benchmark.
5. **Card** - write `docs/arch-experiments/<id>.md` with per-seed numbers, confidence intervals,
   ablation table, MLflow run ids and the demo clip link.

Finish with an explicit verdict line: `ARCH: SIGNIFICANT`, `ARCH: NO EFFECT`,
`ARCH: INCOMPLETE (n/3 seeds)` or `ARCH: QUOTA EXCEEDED`.

An incomplete series never becomes `SIGNIFICANT` because the finished seeds looked good. A
negative result is written up in full - it is a result, not a failed task.
