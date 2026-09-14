# Contributing to OpenSurgicalVision

Thank you for your interest in contributing to OpenSurgicalVision (OSV)!

## 1. Fundamental Contribution Rules

1. **Issue-First Policy:**
   - Every Pull Request MUST reference an open, assigned issue (e.g. `Fixes #123`).
   - If you want to work on something, please comment on the issue and request assignment.
   - Unsolicited PRs or automated PR-bots without assigned issues will be flagged as `invalid` by our triage workflow.
2. **Zero PHI Guarantee:**
   - Under NO circumstances may raw medical images, private patient metadata, or DICOM files with unprotected tags be committed to git.
   - All dataset additions must pass the 4-layer de-identification pipeline (`osv.deid`).
3. **Developer Certificate of Origin (DCO):**
   - All commits must include a sign-off line: `git commit -s -m "feat: your description"`.
4. **AI-First Tooling:**
   - Do NOT edit `.claude/CLAUDE.md`, `.cursor/rules/`, or `AGENTS.md` directly.
   - Edit the canonical sources in `.ai/context.md` or `.ai/prompts/`, then run `make setup-ai`.
   - See **[docs/AI_AGENTS_GUIDE.md](docs/AI_AGENTS_GUIDE.md)** for how to actually use the
     skills (`/deid`, `/qc`, `/exp`, ...) and what the 9 background agents do day to day.

## 2. Development Setup

```bash
# 1. Fork & clone
git clone https://github.com/opensurgicalvision/osv.git
cd open-surgical-vision

# 2. Virtual env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"

# 3. Setup AI tooling
make setup-ai

# 4. Run tests
pytest
```

## 3. Code Standards
- Linting & Formatting: `make lint` and `make format`.
- Strict typing with `mypy`.
- Coverage threshold >= 75%.
