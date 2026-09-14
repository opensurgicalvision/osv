# ADR 0002: Accepting a NonCommercial dataset into an open-source benchmark

- **Status:** Accepted
- **Deciders:** R0 (project owner)
- **Date:** 2026-08-30

## Context & Problem Statement

CholecSeg8k is the first dataset onboarded into the benchmark. Its licence is
**CC BY-NC-SA 4.0**: attribution required, share-alike, and **non-commercial
use only**.

OSV describes itself as open source. Its code is Apache-2.0 and its own
annotations are CC BY-NC-SA 4.0. But a dataset's licence travels with the
dataset: anyone who evaluates against the portion of the benchmark that
contains CholecSeg8k inherits the NC restriction for that portion, whether or
not they read this file. "Open source" as a project description and "you may
not use this commercially" as a data term sit uncomfortably together, and a
user who discovers the tension after building on the benchmark has a real
complaint.

So the question is not whether the licence permits what we want to do -- it
plainly does -- but whether a benchmark that calls itself open can contain
data that is not free for any use, and if so, how that is made impossible to
miss.

## Decision Drivers

- The benchmark is only useful if it contains the datasets the field actually
  uses, and the well-annotated laparoscopic ones are largely NC.
- A restriction a user discovers late is worse than one they see immediately.
- The project must not imply a freedom it cannot grant.
- Whatever is decided has to be checkable by someone who was not in the room.

## Considered Options

1. **Refuse NC datasets entirely.** Perfectly consistent, and it removes
   CholecSeg8k, Cholec80 and most of the surgical-vision field's annotated
   data. The benchmark would be clean and nearly empty.
2. **Accept NC data silently.** Onboard it, describe the project as open
   source, and let the licence live in a file most people will not open. This
   is the option that produces an angry issue eighteen months from now.
3. **Accept NC data, and make the restriction structural.** Onboard it, record
   the acceptance as a decision rather than a preference, and surface the
   restriction wherever the data is described.

## Decision Outcome

**Option 3.** CholecSeg8k is onboarded, and its NonCommercial clause is
accepted as a condition of onboarding rather than treated as a detail.

The acceptance is the project owner's call, made on 2026-08-30, and it is
recorded here so that the record is a document rather than a conversation
someone has to have been part of.

Requirements that follow:

- Every dataset's licence, including whether it permits commercial use, is
  stated in its Data Card under "License & Redistribution Constraints". That
  section is not optional and not a summary.
- The manifest that authorises onboarding (`osv/datasets/manifests/*.yaml`)
  names the licence and cites this ADR where the licence is NC.
- Project-level descriptions must not claim that the benchmark as a whole is
  free for commercial use. The code is; the data is per-dataset.
- A future dataset whose licence forbids redistribution of individual frames
  cannot supply demo-clip frames at all -- see R-26 and
  `demo-assets/allowlist.yaml`, where licence review is one of the two bars a
  frame must clear.

### Consequences

Positive: the benchmark can contain the data the field actually uses, and the
restriction is visible at the point where someone would care about it.

Negative: OSV is not uniformly reusable. A commercial user must check, dataset
by dataset, which parts of the benchmark they may use -- and that checking is
work we are pushing onto them rather than eliminating. That cost is accepted
deliberately; the alternative was a benchmark with almost no data in it.

This decision covers the NC clause only. It is not a judgement on CholecSeg8k's
upstream provenance, which the Data Card tracks as a separate open item.

## Related

- `docs/data-cards/cholecseg8k.md` -- the licence terms in full
- `osv/datasets/manifests/cholecseg8k.yaml` -- the manifest this authorises
- `.ai/rules.md` -- R-23 (a research agent runs only against a reviewed manifest)
