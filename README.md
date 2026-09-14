# OpenSurgicalVision (OSV)

<div align="center">

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Data License](https://img.shields.io/badge/Data_License-CC_BY--NC--SA_4.0-lightgrey.svg)](LICENSE-DATA)
[![CI](https://github.com/opensurgicalvision/osv/actions/workflows/ci.yml/badge.svg)](https://github.com/opensurgicalvision/osv/actions/workflows/ci.yml)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97-OpenSurgicalVision-yellow)](https://huggingface.co/open-surgical-vision)
[![Docs](https://img.shields.io/badge/docs-MkDocs_Material-blue)](docs/)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**An open-source benchmark, standardized dataset hub, and reproducible baseline model zoo for laparoscopic computer vision and surgical scene understanding.**

</div>

---

> ### ⚠️ MANDATORY CLINICAL & REGULATORY DISCLAIMER
>
> **RESEARCH USE ONLY — NOT FOR CLINICAL USE.**
>
> OpenSurgicalVision and its accompanying models, datasets, annotations, and tools are developed solely for research, academic benchmarking, simulation, and educational purposes. This software is **NOT** a medical device, is **NOT** cleared under FDA 510(k)/PMA or EU MDR 2017/745, and must **NEVER** be used in direct clinical diagnosis, surgical decision making, or patient care.
>
> See [docs/clinical-disclaimer.md](docs/clinical-disclaimer.md) for full legal terms.

---

## 🎯 What We Do & What We Do NOT Do

### We Do:
1. **Standardize Open Datasets:** Aggregate existing laparoscopic datasets (Cholec80, CholecSeg8k, EndoVis, TotalSegmentator) into a unified Python API with **strict patient-level splits**.
2. **Reproducible Benchmarks:** Provide deterministic evaluation harnesses, inter-rater metrics (Cohen/Fleiss $\kappa$, Dice, IoU), and public leaderboards.
3. **5 Baseline Models:** Release pre-trained models on Hugging Face Hub (tool segmentation, anatomy parsing, phase recognition, 3D CT preop, smoke removal) with Model Cards.
4. **Surgical Augmentations (`osv.augment`):** Two-tier domain augmentations: L1 on-the-fly (elastic deformation, defocus, noise) and L2 offline static datasets (realistic smoke, blood splatter, glare).
5. **Quality & Privacy Gates:** Enforce 4-layer de-identification (DICOM PS3.15, private tag stripping, OCR burned-in text detection, 3D defacing) and automation bias audits.

### We Do NOT:
- ❌ **We do NOT build medical devices.** (Strictly non-clinical research).
- ❌ **We do NOT accept raw PHI/PII.** (Zero unprotected patient data).
- ❌ **We do NOT redistribute restricted datasets.** (We provide verified download scripts, checksums, and patient splits).

---

## 🏗️ Repository Architecture

```
open-surgical-vision/
├── .ai/                       # Canonical vendor-neutral AI prompts, context & MCP config
├── .claude/                   # Generated Claude assistant rules, skills & agents
├── .cursor/rules/             # Generated Cursor rules
├── .github/                   # CI/CD workflows, issue templates, PR triage filter
├── osv/                       # Core Python package
│   ├── datasets/              # Unified loaders & converters (Cholec80, EndoVis...)
│   ├── deid/                  # 4-layer de-identification & PHI defense
│   ├── annotate/              # SAM 2 pre-annotation & CVAT/Label Studio connectors
│   ├── augment/               # L1 (on-the-fly) & L2 (pre-generated) augmentations
│   ├── models/                # Baseline architectures (M1–M5)
│   ├── train/                 # Hydra trainer templates & mixed precision
│   ├── eval/                  # Inter-rater metrics & automation bias testing
│   ├── robustness/            # Edge-case suite (smoke, blood, glare, defocus)
│   ├── deploy/                # ONNX & TensorRT export (<=50ms latency budget)
│   └── serve/                 # FastAPI demo server with mask streaming
├── benchmarks/                # Leaderboard & golden test benchmarks
├── mcp-servers/               # 6 project-specific Model Context Protocol servers
├── notebooks/                 # Educational tutorials & getting-started guides
├── papers/                    # LaTeX sources for scientific publications
└── docs/                      # Full documentation, Data Cards, Model Cards, Ethics
```

---

## ⚡ Quickstart (5 Minutes)

### Installation

```bash
# Clone repository
git clone https://github.com/opensurgicalvision/osv.git
cd open-surgical-vision

# Create virtual environment and install in editable mode
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
pip install -e ".[dev,docs]"
```

### Loading a Dataset with Strict Patient Isolation

```python
import osv

# Load dataset with strict patient-level split (no frame leakage)
dataset = osv.datasets.load("cholecseg8k", split="train")
print(dataset["info"])
```

### Running Model & Latency Evaluation

```python
from osv.eval import compute_dice
from osv.deploy import get_latency_budget
import numpy as np

# Evaluate mask agreement
pred = np.ones((512, 512), dtype=np.uint8)
gt = np.ones((512, 512), dtype=np.uint8)
dice_score = compute_dice(pred, gt)
print(f"Dice score: {dice_score:.4f}")

# Check real-time edge latency budget (<=50 ms, >=30 FPS)
budget = get_latency_budget()
print(f"Target Latency p95: {budget['target_latency_p95_ms']} ms")
```

---

## 🤖 AI-First Contributor Workflow

OpenSurgicalVision is designed from the ground up for human-AI collaboration:
- **Single Source of Truth:** Edit `.ai/context.md` or `.ai/prompts/` to update instructions.
- **Multi-IDE Sync:** Run `make setup-ai` to automatically synchronize configs for Claude, Cursor, Copilot, Aider, and Antigravity.
- **11 MCP Servers:** Access datasets, MLflow runs, annotations, and literature directly via Model Context Protocol.

```bash
# Regenerate AI IDE configs
make setup-ai

# Verify sync in CI
make check-ai
```

**New to the project?** [docs/AI_AGENTS_GUIDE.md](docs/AI_AGENTS_GUIDE.md) walks through setup,
every `/command`, and what each of the 9 background agents does — start there.

---

## 🩺 Clinical Governance & Ethics

- **Clinical Lead (RC):** Practicing surgical lead with absolute authority over anatomical definitions, contested boundary adjudications ([docs/adjudications.md](docs/adjudications.md)), and guideline approvals.
- **Ethics Statement & IRB:** Documented in [docs/ethics.md](docs/ethics.md).
- **Semi-Annual Regulatory Log:** Documented in [docs/regulatory-log.md](docs/regulatory-log.md).

---

## 🤝 Contributing

We welcome contributions from ML engineers, clinicians, data scientists, and students!

1. Check our [good first issues](https://github.com/opensurgicalvision/osv/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
2. **Issue-First Policy:** Every Pull Request MUST be linked to an existing Issue with approved assignment. (Automated PRs without assigned issues will be closed by `pr-triage`).
3. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

## 📜 Licenses

- **Software & Code:** [Apache 2.0](LICENSE)
- **Annotations & Derivative Data:** [CC BY-NC-SA 4.0](LICENSE-DATA)
- **Documentation & Presentations:** [CC BY 4.0](docs/clinical-disclaimer.md)
