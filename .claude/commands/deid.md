---
description: Run the 4-layer de-identification audit on a dataset path
argument-hint: <dataset-path>
---

Run the full de-identification audit on `$ARGUMENTS` using the `deid-audit` skill.

Report each layer separately and never summarise a failure into a pass:

1. **PS3.15 standard tags** - list every tag found, not just a count.
2. **Private tags** (odd groups) - removed wholesale unless explicitly allow-listed.
3. **Burned-in pixel text** - OCR every frame and slice. The `BurnedInAnnotation` tag is
   untrustworthy and frequently absent; ignore it and scan anyway.
4. **Indirect identifiers** - reconstructable face on head CT/MRI, unique implants, device serials.

Finish with an explicit verdict line: `DEID: PASS` or `DEID: FAIL (<layer>)`.
On FAIL, name the offending files and stop. Do not propose committing anything.
