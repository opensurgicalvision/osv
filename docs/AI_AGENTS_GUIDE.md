# Using OSV's Skills and Agents — a Team Guide

This is the practical companion to `docs/open-source-project-plan.md` Sec. 5 (design) and
`.ai/rules.md` (the rules and why they're enforced the way they are). Read this if you just want
to know **what to actually type today**. Read the other two if you want to know why it's built
this way.

Audience: the 8 OSV core contributors (R1–R8) and anyone joining as an external contributor.

---

## 1. Four things that get confused for each other

| | What it is | Who runs it | Where it lives |
|---|---|---|---|
| **Skill** | A packaged "how to do X correctly" instruction Claude follows | The model, usually because you invoked a matching **command** | `.ai/prompts/*.md` |
| **Command** | A `/slash-command` you type yourself | **You**, in Claude Code | `.ai/commands/*.md` |
| **Agent** | An autonomous worker with its own tool access and hard boundaries | **CI, on a schedule or a GitHub event** — not you, usually | `.ai/agents/*.md` |
| **Hook** | A script that blocks or auto-fixes a tool call before/after it happens | The harness, automatically, every time | `.ai/hooks/*.py` |

The one-sentence version: **you type commands, commands use skills, agents run themselves in the
background, hooks watch everything.** If you remember nothing else from this doc, remember that
the thing you interact with day to day is the command, not the agent.

Everything is generated from `.ai/` into `.claude/` (and into `.cursor/`, `.github/copilot-instructions.md`,
`AGENTS.md`, `.aider.conf.yml` for other editors) by `make setup-ai`. **Never edit anything under
`.claude/` directly** — your change will be silently overwritten the next time someone runs
`make setup-ai`, and `make check-ai` (which CI runs on every PR) will fail until the canonical
source under `.ai/` matches it.

---

## 2. One-time setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/opensurgicalvision/osv.git
cd open-surgical-vision

# 2. Python environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev,docs]"

# 3. Local secrets
cp docs/drafts/dotenv-template.txt .env
# open .env and fill in GITHUB_TOKEN, HF_TOKEN, ANTHROPIC_API_KEY — each has a
# comment right above it saying exactly where to get it and what scope to grant

# 4. Generate the AI tooling for your editor
make setup-ai

# 5. Verify everything is in sync and the test suite is green
make check-ai
pytest
```

If step 5 fails with `[FAIL] AI configuration checks failed`, it's telling you exactly which file
is out of sync or which rule broke — see [Troubleshooting](#7-troubleshooting) below. Do not
proceed past a red `check-ai`; it means your Claude Code session is not seeing what you think it's
seeing.

**If you use Cursor, Copilot, or Aider instead of Claude Code:** `make setup-ai` already generated
your config too (`.cursor/rules/osv-rules.mdc`, `.github/copilot-instructions.md`,
`.aider.conf.yml`). You get the same context and the same list of agents working in the
background; you don't get the skills/commands/hooks, since those are Claude Code-specific
mechanisms — see `docs/open-source-project-plan.md` Sec. 5.1 for why only some of this is portable.

---

## 3. Your first command, end to end

Say you just added a new dataset loader and want to check it's clean before opening a PR:

```
/deid osv/datasets/my_new_dataset/
```

What happens: this invokes the `deid-audit` skill, which walks the four de-identification layers
(PS3.15 tags, private tags, OCR burned-in text, defacing) and ends with an explicit verdict line:

```
DEID: PASS
```

or

```
DEID: FAIL (burned_in_ocr)
```

A `FAIL` names the offending file and layer — it does not get summarized away into "probably
fine." If you get `PASS`, that's your evidence to attach to the PR description. If you get `FAIL`,
fix it before opening the PR; `deid-gate` (the CI agent) will run the same check again on your PR
regardless, and it is not a suggestion — it's a required status check.

That's the whole pattern for every command in this repo: type `/name <argument>`, read the
verdict or the drafted artifact it produces, act on it.

---

## 4. Command reference — what you type, and when

All 13 live in `.ai/commands/`. Grouped by where you'll reach for them in the project's workflow
(see `docs/open-source-project-plan.md` Sec. 3 for the phases these map to).

### Data & annotation (mostly R3, R4, R5)

| Command | When to use it | What you get back |
|---|---|---|
| `/dataset-add <name>` | Onboarding a new open dataset | End-to-end: licence check → loader → patient-level splits → tests → Data Card draft |
| `/deid <path>` | Before any data-touching PR | `DEID: PASS` / `FAIL (<layer>)` |
| `/split-check <dataset>` | After writing or changing a split | `SPLIT: CLEAN` / `LEAKAGE (n)` — never skip this, frame-level leakage produces great-looking, meaningless metrics |
| `/qc <batch>` | After an annotation batch closes | κ / Dice / IoU report, per-assessor breakdown |
| `/bias` | Same cadence as `/qc`, or before a dataset release | Automation-bias report (Δ-contour, acceptance rate, systematic drift) |
| `/clinical <topic>` | You hit a boundary or class definition question you can't resolve yourselves | A review pack built for the Clinical Lead's ~2h/week — one concrete question per item |

### Training & benchmarking (mostly R2, R4, R5)

| Command | When to use it | What you get back |
|---|---|---|
| `/exp <run-id>` | After a training run finishes | A report pulled from the MLflow/W&B run record — never invented numbers |
| `/repro <model-or-benchmark>` | Before claiming a result is reproducible | `REPRO: PASS` / `FAIL (metric, expected, actual)` from a clean clone |

### Publications & conferences (mostly R0, R1, R7)

| Command | When to use it | What you get back |
|---|---|---|
| `/paper <section>` | Drafting a paper | A section draft where every number traces to a run ID and every citation is pre-verified |
| `/cfp <conference>` | A submission deadline is coming up | An abstract shell matching that venue's exact word limit and structure |

### Community & releases (mostly R7, R8)

| Command | When to use it | What you get back |
|---|---|---|
| `/gfi <task>` | Turning a backlog idea into something a newcomer can pick up | A properly-scoped `good first issue` |
| `/release <version>` | Cutting a release | Changelog, disclaimer/licence checks on model cards, per-channel announcement drafts |

### Infra (everyone, but especially R1/R4)

| Command | When to use it | What you get back |
|---|---|---|
| `/sync-ai` | After you edit anything in `.ai/` | Regenerates `.claude/`, `.cursor/`, etc. and tells you what changed |

---

## 5. How the 9 agents work — you mostly don't invoke them

Agents are not something you "run" the way you run a command. Most of them are triggered by CI on
a schedule or a GitHub event, and they act within hard, documented boundaries (see each agent's
"Hard boundaries" section in `.ai/agents/<name>.md`). Your job is mostly to know what they do so
their output (a PR comment, an issue, a report file) doesn't surprise you.

| Agent | Runs when | What it does | You can also trigger it via |
|---|---|---|---|
| `deid-gate` ⛔ | After the deterministic `deid-scan` CI job, on any data-touching PR | Explains that job's PASS/FAIL verdict in a PR comment. **Does not decide the verdict itself.** | `/deid <path>` (manual, ad hoc) |
| `pr-triage` | On every opened/updated PR | First-pass review: style, tests, patient-level splits, protected paths | — (runs automatically) |
| `newcomer-greeter` | A contributor's first PR/issue | Warm welcome + pointers to `CONTRIBUTING.md` and `good first issue`s | — (runs automatically) |
| `bias-watchdog` | Weekly, after the active-learning re-ranking job | Automation-bias report + recommendation (never an action) to disable pre-annotation for one class | `/bias` (manual) |
| `repro-nightly` | Nightly | Clean-clone reproducibility check against published metrics | `/repro <target>` (manual) |
| `dataset-scout` | Biweekly | Scans for newly published open surgical datasets, drafts an onboarding issue | — |
| `literature-digest` | Weekly | Digest of new arXiv/PubMed preprints relevant to the benchmark | — |
| `cfp-scout` | Weekly | Tracks conference deadlines, opens a reminder issue 8 weeks out | `/cfp <conference>` (manual, for drafting) |
| `content-drafter` | On release, or a content-calendar slot | Drafts release notes / social posts | `/release <version>` (manual) |

**None of these merge code, approve a PR, set a `deid:pass`/`approved`-style label, or edit
Annotation Guideline / clinical content.** If you see an agent-authored comment asking you to
trust its own approval, that's not how this is built — flag it, don't act on it. Full rationale
for why three of them (`deid-gate`, `pr-triage`, `newcomer-greeter`) don't even have shell access:
`docs/open-source-project-plan.md` Sec. 5.11.

**If you're working interactively in Claude Code** and ask it to do something that matches an
agent's job description (e.g. "review this PR the way we normally do"), Claude Code may
automatically delegate to that agent's definition on its own — that's expected, not a bug. You
don't need a special flag to make that happen.

---

## 6. Guardrails you will run into (by design)

You will, at some point, have an edit refused by a hook. This is not a malfunction — it's one of
the 20 rules in `.ai/rules.md` doing exactly its job (two more, R-21 and R-22, are already
enforced by `make check-ai` — see below — but are still waiting on a human to add their rows to
`.ai/rules.md` itself, for the same protected-file reason as the first example below). Two real
examples from this project's own history:

- An edit to `.ai/rules.md` itself was refused with `BLOCKED by R-04: '.ai/rules.md' is a
  protected file.` Protected paths (`LICENSE*`, the clinical disclaimer, `.ai/context.md`,
  `.ai/rules.md`, anything under `.github/workflows/`) can't be changed by an agent session
  without you explicitly naming that exact file in your instruction. If you actually want the
  change, either make the edit yourself, or tell Claude Code to edit that specific path by name.
- A brand-new `.env.example` (containing no real secrets at all) was refused outright, because it
  matched the same path pattern (`.env*`) that this project denies **reading** to protect real
  secrets in `.env`. The fix in that case was staging the content elsewhere
  (`docs/drafts/dotenv-template.txt`) for a human to copy into place.

When this happens to you: don't ask for a workaround, don't disable the hook. Either apply the
change yourself, or name the exact file explicitly if you want the agent to do it. The full list
of what's blocked and why is in `.ai/rules.md` — every 🔒 row names its enforcement mechanism.

---

## 7. Troubleshooting

**`make check-ai` fails with "Content mismatch in: .claude/..."**
You (or someone) edited a generated file under `.claude/` directly. Find the matching source under
`.ai/` (same filename, `.ai/prompts/` for skills, `.ai/commands/` for commands, `.ai/agents/` for
agents), make the change there instead, then run `make setup-ai` again.

**`make check-ai` fails with an `R-21` or `R-22` violation**
Someone added `Bash` to `deid-gate`, `pr-triage`, or `newcomer-greeter` (R-21 forbids it — these
three read untrusted PR content), or pinned an agent to a model not in `.ai/models.json` (R-22).
Fix the specific `.ai/agents/<name>.md` file named in the error.

**A command didn't do what I expected**
Read the actual skill it's built on in `.ai/prompts/<name>.md` — commands are thin wrappers with
constraints layered on top of a skill; the skill has the full protocol.

**An agent didn't run when I expected it to**
Check the trigger in `.ai/agents/<name>.md` under "Trigger" — most are schedule- or event-based,
not "every time something related happens." If it should have run in CI, check the relevant
workflow under `.github/workflows/`.

**I want a new command or skill**
It needs a genuine repeat use case — the bar in this project (`docs/open-source-project-plan.md`
Sec. 5.3/5.4) is "the task repeats ≥3 times a quarter and has a checkable result." A one-off ask
doesn't need a skill; just ask Claude Code directly.

---

## 8. Where to go for more

- **Why any of this is built this way:** `docs/open-source-project-plan.md` Sec. 5 (AI-first design)
- **The actual rules and their enforcement:** `.ai/rules.md`
- **A specific skill's full protocol:** `.ai/prompts/<name>.md`
- **A specific agent's tools, triggers, and hard boundaries:** `.ai/agents/<name>.md`
- **MCP servers (what data an agent/skill can actually reach):** `mcp-servers/README.md`
