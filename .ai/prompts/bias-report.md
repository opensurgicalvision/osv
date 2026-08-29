# Skill: bias-report
**Priority:** P0 | **Owner:** R5 | **Scope:** Annotation & AI Alignment

## Purpose
Generates periodic automation bias audit reports evaluating whether annotators blindly accept SAM 2 suggestions.

## Key Metrics
1. **Delta-Contour Dice:** Compare pre-annotated frames against blind control frames (target >= 0.90).
2. **Acceptance Rate:** Track percentage of unedited AI suggestions (target < 60%).
3. **Class Area Drift:** Detect systematic boundary shrink/inflation per anatomical class.
4. If a class violates thresholds, recommend disabling SAM 2 pre-annotation for that specific class.
