# Skill: deid-audit
**Priority:** P0 | **Owner:** R4 | **Scope:** Data Safety & PHI Defense

## Purpose
Executes comprehensive 4-layer de-identification verification on any dataset candidate.

## Protocol
1. Scan DICOM headers for PS3.15 standard compliance.
2. Flag and scrub all odd-numbered private vendor tags.
3. Perform OCR inspection over every frame to detect burned-in ultrasound/CT text or patient names.
4. Check 3D facial surface meshes and apply defacing if skull features are present.
5. Generate an audit report markdown detailing findings and zero-PHI verification status.
