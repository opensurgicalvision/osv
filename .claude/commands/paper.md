---
description: Draft a paper section with verified citations
argument-hint: <section-name>
---

Draft the `$ARGUMENTS` section using the `paper-section` skill.

Hard constraints:
- **Every number traces to an MLflow run id.** No figure originates from your own output (R-15).
- **Every citation is verified** against arXiv/PubMed through MCP before it appears. An
  unverifiable reference is dropped, never approximated (R-16). A hallucinated citation is
  grounds for retraction.
- Ethics Statement and Limitations are mandatory sections, not optional polish.
- Mark anything you could not verify with `[UNVERIFIED]` inline rather than smoothing it over.

Venue conventions come from `docs/talks/` and the CFP; ask if the target venue is unclear.
