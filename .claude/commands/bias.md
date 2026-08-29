---
description: Automation-bias report for SAM 2 pre-annotation
---

Produce the automation-bias report using the `bias-report` skill.

Report, per class:
- Delta-contour: Dice between "annotated with pre-annotation" and "annotated from scratch"
  on control frames (threshold >= 0.90)
- Acceptance rate: share of SAM 2 masks accepted with zero edit clicks (red flag above 60%)
- Time per frame against the median (suspicious below 40%)
- Systematic area bias (drop the class from pre-annotation above 5%)

Control frames are 10% of the queue, unmarked, and must never be disabled (R-20).

Recommend disabling pre-annotation **per class**, never globally: instruments have crisp edges
and SAM 2 is reliable on them; ducts and dissection planes are where it quietly drifts.
