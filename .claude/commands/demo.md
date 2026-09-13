---
description: Render the demo clip for a finished run and file it as an artifact
argument-hint: <run-id>
---

Render the demo clip for run `$ARGUMENTS` using the `demo-clip` skill.

1. Resolve the run and its baseline. No baseline means render the candidate alone - never invent
   a comparison.
2. Select frames **from `demo-assets/allowlist.yaml` only**, weighted towards the failure cases
   the metrics flagged. A frame outside the allowlist stops the render; it is not swapped for a
   similar one.
3. Render through `python -m osv.demo --run-id <id> --frame-list <file> --output <path outside
   the repo>`. The run id and `RESEARCH USE ONLY - NOT FOR CLINICAL USE` are burned in by the
   renderer unconditionally - there is no flag for it.
4. Store as an artifact of the same run. Never write the video into the repository tree.
5. Add a markdown link plus one line of context to `docs/arch-experiments/<id>.md` and to the MR
   description.

Finish with an explicit verdict line: `DEMO: OK <artifact-link>` or
`DEMO: BLOCKED (<reason>)`.

Publishing to Hugging Face, YouTube or social channels is not part of this command. That is a
human decision taken from the finished artifact.
