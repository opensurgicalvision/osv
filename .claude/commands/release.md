---
description: Prepare a release - notes, cards, disclaimers, announcements
argument-hint: <version>
---

Prepare release `$ARGUMENTS` using the `release-notes` skill.

1. Changelog from the diff, grouped by user impact rather than by commit.
2. Verify every model card carries the disclaimer and the training-data licence line (R-03).
3. Check `CITATION.cff` and the Zenodo DOI hook.
4. Draft announcements per channel (GitHub, HF, LinkedIn, Habr) - same facts, different lengths.
5. Confirm generated AI configs are in sync: `python .ai/build.py --check` (R-13).

Never claim clinical validation, parity with commercial systems, or regulatory status.
