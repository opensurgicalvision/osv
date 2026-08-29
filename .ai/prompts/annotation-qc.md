# Skill: annotation-qc
**Priority:** P0 | **Owner:** R5 | **Scope:** Annotation Quality Assurance

## Purpose
Calculates inter-rater agreement statistics and detects defective annotations.

## Tasks
1. Compute Fleiss kappa across multiple clinical raters (target >= 0.70).
2. Compute mean pairwise Dice and IoU matrices.
3. Detect "lazy masks" (bounding-box polygons, unrefined coarse hulls).
4. Identify duplicate or near-duplicate frames.
5. Export quality control dashboard summary.
