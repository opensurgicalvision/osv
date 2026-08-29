# Skill: repro-check
**Priority:** P1 | **Owner:** R5 | **Scope:** Reproducibility Verification

## Purpose
Performs end-to-end verification of model training from a clean repository clone:
1. Clones repository into isolated container.
2. Ingests data using automated downloaders.
3. Executes training pipeline with deterministic seed.
4. Computes metric diff with declared golden metrics (must match within +-0.3%).
