---
description: Regenerate and verify the AI tooling configs
---

Regenerate vendor configs from the canonical `.ai/` source:

```
python .ai/build.py
python .ai/build.py --check
```

If `--check` fails, someone edited a generated file directly. Port the change back into `.ai/`
(context, rules, prompts, hooks or commands) and regenerate. Never hand-patch `.claude/`,
`AGENTS.md`, `.cursor/`, `.github/copilot-instructions.md` or `.aider.conf.yml` (R-13).

Then summarise what changed and which tools are affected.
