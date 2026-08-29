# Skill: dataset-onboard
**Priority:** P0 | **Owner:** R4 | **Scope:** Data Aggregation

## Purpose
Automates the full cycle of onboarding an open surgical dataset into OpenSurgicalVision.

## Workflow
1. Download dataset using official public scripts or URL.
2. Verify checksums against `docs/data-cards/licenses.md`.
3. Run 4-layer de-identification check (`osv.deid.verify_no_phi`).
4. Generate strictly patient-isolated splits (train/val/test).
5. Implement converter to standard COCO (2D) or NIfTI (3D) in `osv/datasets/`.
6. Add unit test `test_no_patient_leakage()` in `tests/`.
7. Generate template Data Card in `docs/data-cards/<dataset_name>.md`.
