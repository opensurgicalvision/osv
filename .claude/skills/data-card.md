<!-- AUTO-GENERATED from .ai/prompts/data-card.md -->

# Skill: data-card
**Priority:** P0 | **Owner:** R5 | **Scope:** Data Documentation

## Purpose
Generates a complete Data Card adhering to the Datasheets for Datasets standard for a dataset in `osv/datasets/`.

## Sections to Populate
1. **Dataset Origin:** Original authors, institution, year, publication DOI.
2. **License & Restrictions:** Commercial/non-commercial, attribution, distribution rights.
3. **Clinical Domain:** Modality (laparoscopy, endoscopy, CT), procedure type, anatomical structures.
4. **De-identification Status:** Results of `deid-audit`, confirmation of zero PHI.
5. **Known Biases:** Camera models, illumination settings, patient demographic limits.
6. **Patient Splits:** Document patient IDs per split and verify zero cross-contamination.
