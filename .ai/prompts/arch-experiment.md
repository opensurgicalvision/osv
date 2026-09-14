# Skill: arch-experiment
**Priority:** P0 | **Owner:** R2 | **Scope:** Architecture Sandbox

## Purpose
Turns one architecture hypothesis into a comparable, reproducible result: config from the
registry, at least 3 seeds, confidence intervals, ablation, and an experiment card that someone
else can re-run from scratch. The sandbox runs from Phase 1 on open datasets (plan Sec. 1.5).

## Protocol (non-negotiable - a run outside it is not an experiment)
1. **Fixed split.** The frozen patient-level split from the repository, versioned in DVC (R-08).
   Never a fresh random split, never a frame-level one.
2. **Fixed budget.** Same epochs / batch size / GPU-hours as the baseline it is compared against.
   Otherwise the comparison measures budget, not architecture.
3. **>= 3 seeds.** Report mean and confidence interval across seeds. Seed spread in segmentation
   routinely exceeds the effect being claimed.
4. **Validation only.** The held-out test set is not touched here at all - it is a separate DVC
   remote the runner cannot read (R-25), and its use is counted in `docs/BENCHMARK.md`.
5. **Ablation.** Any block that goes into the benchmark has a run without it, same split, same
   budget. "We changed five things and it improved" is an anecdote.
6. **Config from the registry.** Blocks come from `osv/arch/registry.py`. Widening the search
   space is a human PR reviewed by R1, never an improvisation inside a run.

## Output: `docs/arch-experiments/<id>.md`
- Hypothesis in one sentence, and what result would falsify it.
- Config diff against the baseline, plus `config_hash`.
- Per-seed metrics, mean, confidence interval, per-class breakdown.
- Ablation table.
- MLflow parent run id and child run ids, link to the demo clip.
- Verdict and one paragraph of interpretation.

## Verdicts
- `ARCH: SIGNIFICANT` - >= 3 finished seeds and non-overlapping confidence intervals.
- `ARCH: NO EFFECT` - series complete, intervals overlap. Publish the card anyway.
- `ARCH: INCOMPLETE (n/3 seeds)` - series unfinished. Cannot be upgraded to SIGNIFICANT on the
  strength of the seeds that did finish.
- `ARCH: QUOTA EXCEEDED` - weekly GPU budget spent; state is saved and the series resumes.

## Rules
A negative result is written up with the same care as a positive one - it is half the value of an
educational project and the half nobody publishes. No number in a card comes from model output;
every one traces to an MLflow run (R-15). Nothing in a card claims clinical quality (R-14).
