<!-- AUTO-GENERATED from .ai/prompts/model-card.md -->

# Skill: model-card
**Priority:** P0 | **Owner:** R2 | **Scope:** Model Releases

## Purpose
Generates official model documentation for Hugging Face Hub releases.

## Mandatory Elements
1. Top-level disclaimer banner: `RESEARCH USE ONLY — NOT FOR CLINICAL USE`.
2. Architecture details, parameter counts, and backbone weights.
3. Training dataset list and strict inheritance of most restrictive dataset license.
4. Quantitative benchmarks: mIoU, Dice, inference latency p50/p95 on RTX 4090 / Jetson AGX Orin.
5. Robustness evaluation across smoke levels, blood splatter, and defocus.
