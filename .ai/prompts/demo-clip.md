# Skill: demo-clip
**Priority:** P1 | **Owner:** R6 | **Scope:** Experiment Demos & Content

## Purpose
Turns a finished run into a 20-40 second clip that shows how the model behaves - including where
it fails - and files it where a clip is allowed to live. Rendered at experiment time, not
assembled later under a content deadline (plan Sec. 5.13, Sec. 6.2).

## What the clip contains
1. Prediction overlay on video, baseline left / candidate right where a baseline exists.
2. Frame selection weighted towards the failure cases the metrics flagged - smoke, blood on the
   lens, defocus, rare anatomy. A reel of only the good frames is marketing, not evidence.
3. Burned into the frame, not captioned: run id, commit hash, and
   `RESEARCH USE ONLY - NOT FOR CLINICAL USE`. Burned in because a caption can be cropped off.

## Where frames come from
`demo-assets/allowlist.yaml` and nowhere else: entries whose licence permits redistribution and
which have passed the burned-in-text OCR scan. An empty allowlist renders nothing - the correct
default, not a bug. Adding a frame is a human PR; the `demo_guard` hook refuses the rest (R-26).

## Where the clip goes
| Purpose | Destination | Written by |
|---|---|---|
| Primary storage | Artifact of the same MLflow / W&B run | the run's own job |
| Release copy | GitHub Release asset | deterministic release job on protected `main` |
| Public showcase (HF Space, YouTube, social) | manually, from the finished artifact | R7 / R6 |

Never into git: `*.mp4` under the repo tree is blocked (R-01). The PR, the issue and the
experiment card carry a markdown link and one line saying what the clip shows.

## Verdicts
- `DEMO: OK <artifact-link>`
- `DEMO: BLOCKED (frame not allowlisted | missing disclaimer | output inside repo tree)`

## Rules
The agent never publishes outward - that is a human decision (Sec. 6.3). No caption compares the
project to commercial systems, and none states or implies clinical quality (R-14).
