# Surgical Annotation Guideline v1.0

Official guideline for annotating laparoscopic surgical video frames, anatomical structures, and surgical tools.

## 1. Quality & Agreement Thresholds
- **Inter-rater Agreement:** Fleiss kappa >= 0.70, mean pairwise Dice >= 0.80.
- **Automation Bias Safeguards:**
  - 10% of frames presented without pre-annotation (blind control).
  - Target delta-contour Dice >= 0.90 between pre-annotated and scratch annotations.
  - Acceptance rate of SAM 2 suggestions must stay < 60%.

## 2. Anatomical Classes & Rules
1. **Liver:** Include parenchyma; exclude gallbladder bed when dissected.
2. **Gallbladder:** Include fundus, body, neck; stop at cystic duct junction.
3. **Hepatocystic Triangle / Calot's Triangle:** Critical view of safety landmarks.
4. **Surgical Instruments:** Shaft, joint, and active jaws are annotated with sub-part labels.

## 3. Disputed Boundaries & Adjudications
In cases of severe inflammation or anatomical distortion, mark as `needs-clinician` for review in `docs/adjudications.md`.
