#!/usr/bin/env python3
"""Build and synchronize vendor-specific AI assistant configurations from canonical .ai/ source."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
AI_DIR = ROOT_DIR / ".ai"
PROMPTS_DIR = AI_DIR / "prompts"
COMMANDS_DIR = AI_DIR / "commands"
HOOKS_DIR = AI_DIR / "hooks"
AGENTS_DIR = AI_DIR / "agents"
MCP_FILE = AI_DIR / "mcp" / "servers.json"
CONTEXT_FILE = AI_DIR / "context.md"
RULES_FILE = AI_DIR / "rules.md"
MODELS_FILE = AI_DIR / "models.json"

# R-21: agents that read untrusted PR content (an anonymous fork's diff) are
# never granted Bash -- GitHub interaction goes through narrow, typed MCP
# tools only (osv-github-ro / osv-github-triage). This list is the mechanical
# half of that rule: a future edit that re-adds Bash to one of these agents
# fails CI instead of silently reopening the shell-injection vector.
NO_BASH_AGENTS = frozenset({"deid-gate", "pr-triage", "newcomer-greeter"})


def load_context() -> str:
    if not CONTEXT_FILE.exists():
        raise FileNotFoundError(f"Missing {CONTEXT_FILE}")
    context = CONTEXT_FILE.read_text(encoding="utf-8").strip()
    if RULES_FILE.exists():
        context += "\n\n---\n\n" + RULES_FILE.read_text(encoding="utf-8").strip()
    return context


def load_commands() -> dict[str, str]:
    commands = {}
    if COMMANDS_DIR.exists():
        for file in sorted(COMMANDS_DIR.glob("*.md")):
            commands[file.stem] = file.read_text(encoding="utf-8").strip()
    return commands


def load_hooks() -> dict[str, str]:
    hooks = {}
    if HOOKS_DIR.exists():
        for file in sorted(HOOKS_DIR.glob("*.py")):
            hooks[file.name] = file.read_text(encoding="utf-8")
    return hooks


def load_agents() -> dict[str, str]:
    """Canonical agent definitions. Frontmatter must stay the first bytes of the
    file for Claude Code to parse it, so these are copied to .claude/agents/
    verbatim (see generate_claude) rather than prefixed with a header comment."""
    agents = {}
    if AGENTS_DIR.exists():
        for file in sorted(AGENTS_DIR.glob("*.md")):
            agents[file.stem] = file.read_text(encoding="utf-8").strip()
    return agents


def parse_agent_description(content: str) -> str:
    """Pull the one-line `description:` out of an agent's YAML frontmatter
    without taking a yaml dependency — the frontmatter here is simple enough
    that a line scan is reliable and avoids adding a package for one field."""
    if not content.startswith("---"):
        return ""
    end = content.find("\n---", 3)
    frontmatter = content[3:end] if end != -1 else content[3:200]
    for line in frontmatter.splitlines():
        if line.strip().startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""


def load_mcp() -> dict:
    if not MCP_FILE.exists():
        raise FileNotFoundError(f"Missing {MCP_FILE}")
    return json.loads(MCP_FILE.read_text(encoding="utf-8"))


def load_skills() -> dict[str, str]:
    skills = {}
    if PROMPTS_DIR.exists():
        for file in sorted(PROMPTS_DIR.glob("*.md")):
            skills[file.stem] = file.read_text(encoding="utf-8").strip()
    return skills


def hook_entry(matcher: str | None, script: str) -> dict:
    """One Claude Code hook registration. Hooks run from the repo root."""
    entry: dict = {"hooks": [{"type": "command", "command": f"python .claude/hooks/{script}"}]}
    if matcher is not None:
        entry["matcher"] = matcher
    return entry


def build_hook_config() -> dict:
    """Wire the guards to tool events. See .ai/rules.md for what each one enforces."""
    return {
        "PreToolUse": [
            hook_entry("Write|Edit|NotebookEdit", "phi_path_guard.py"),
            hook_entry("Bash", "bash_guard.py"),
            # R-26: a demo clip is the shortest path from this repo to the public,
            # so the frame allowlist, the burned-in disclaimer and the "no video in
            # git, no publishing outward" boundaries are enforced on both the render
            # command and any attempt to write media into the tree.
            hook_entry("Write|Edit|NotebookEdit", "demo_guard.py"),
            hook_entry("Bash", "demo_guard.py"),
        ],
        "PostToolUse": [
            hook_entry("Write|Edit", "python_format.py"),
            hook_entry("Write|Edit|NotebookEdit", "notebook_guard.py"),
            hook_entry("Write|Edit", "disclaimer_guard.py"),
        ],
        "SessionStart": [hook_entry(None, "session_start.py")],
    }


def build_permissions() -> dict:
    """Deny rules are the mechanical half of .ai/rules.md.

    A rule stated only in prose is a suggestion; these are refusals.
    """
    return {
        "deny": [
            "Read(./.env)",
            "Read(./.env.*)",
            "Read(./**/*.pem)",
            "Read(./**/secrets/**)",
            "Read(./data/raw/**)",
            "Write(./data/raw/**)",
            "Write(./LICENSE*)",
            "Write(./docs/clinical-disclaimer.md)",
            "Write(./.github/workflows/**)",
            "Bash(git commit:*--no-verify*)",
            "Bash(git push:*--force*)",
            "Bash(curl:*)",
            "Bash(wget:*)",
        ],
        "ask": [
            "Bash(dvc push:*)",
            "Bash(git push:*)",
            "Bash(gh pr merge:*)",
            "Bash(gh pr review:*)",
            "Bash(hf upload:*)",
        ],
    }


def generate_claude(
    context: str,
    mcp_data: dict,
    skills: dict[str, str],
    commands: dict[str, str],
    hooks: dict[str, str],
    agents: dict[str, str],
) -> dict[Path, str]:
    files = {}

    # .claude/CLAUDE.md
    claude_md = (
        "<!-- AUTO-GENERATED from .ai/context.md DO NOT EDIT DIRECTLY -->\n\n"
        + context
        + "\n\n## Available OSV Skills\n"
        + "\n".join(f"- `{name}`" for name in skills.keys())
        + "\n\n## Available OSV Commands\n"
        + "\n".join(f"- `/{name}`" for name in commands.keys())
        + "\n\n## Available OSV Agents\n"
        + "\n".join(
            f"- `{name}` - {parse_agent_description(body)}" for name, body in agents.items()
        )
    )
    files[ROOT_DIR / ".claude" / "CLAUDE.md"] = claude_md

    # .claude/settings.json
    settings = {
        "mcpServers": mcp_data.get("mcpServers", {}),
        "autoApprove": [
            "osv-datasets",
            "osv-experiments",
            "osv-leaderboard",
            "osv-cfp",
            "osv-github-ro"
            # osv-github-triage is deliberately NOT auto-approved: it is the
            # only MCP server that writes to GitHub, and every call should be
            # visible for approval even though the label allowlist inside it
            # (see mcp-servers/osv-github-triage/_github_triage_core.py) means
            # a rejected approval is a UX cost, not a security gap.
        ],
        "permissions": build_permissions(),
        "hooks": build_hook_config(),
    }
    files[ROOT_DIR / ".claude" / "settings.json"] = json.dumps(settings, indent=2) + "\n"

    # .claude/commands/<command>.md
    for name, content in commands.items():
        files[ROOT_DIR / ".claude" / "commands" / f"{name}.md"] = content + "\n"

    # .claude/hooks/<hook>.py
    for name, content in hooks.items():
        files[ROOT_DIR / ".claude" / "hooks" / name] = content

    # .claude/mcp/servers.json
    files[ROOT_DIR / ".claude" / "mcp" / "servers.json"] = json.dumps(mcp_data, indent=2) + "\n"

    # .claude/skills/<skill>.md
    for name, content in skills.items():
        files[ROOT_DIR / ".claude" / "skills" / f"{name}.md"] = (
            f"<!-- AUTO-GENERATED from .ai/prompts/{name}.md -->\n\n" + content + "\n"
        )

    # .claude/agents/<agent>.md — copied verbatim: frontmatter must lead the file
    # for Claude Code to parse it, so no header comment goes before the content.
    # A provenance note is appended after the body instead.
    for name, content in agents.items():
        files[ROOT_DIR / ".claude" / "agents" / f"{name}.md"] = (
            content + f"\n\n<!-- AUTO-GENERATED from .ai/agents/{name}.md DO NOT EDIT DIRECTLY -->\n"
        )

    return files


def generate_agents_md(context: str, skills: dict[str, str], agents: dict[str, str]) -> dict[Path, str]:
    content = (
        "# AGENTS.md — OpenSurgicalVision Autonomous AI Directives\n\n"
        "<!-- AUTO-GENERATED from .ai/context.md DO NOT EDIT DIRECTLY -->\n\n"
        + context
        + "\n\n## Registered OSV Skills\n\n"
    )
    for name, skill_body in skills.items():
        content += f"### `{name}`\n\n{skill_body}\n\n---\n\n"

    content += "## Registered OSV Agents\n\n"
    content += (
        "Full definitions (tools, triggers, hard boundaries) live in `.ai/agents/*.md` "
        "and `.claude/agents/*.md` for Claude Code specifically. Summary:\n\n"
    )
    content += "| Agent | Role |\n|---|---|\n"
    for name, agent_body in agents.items():
        content += f"| `{name}` | {parse_agent_description(agent_body)} |\n"

    return {ROOT_DIR / "AGENTS.md": content}


def generate_cursor_rules(context: str, agents: dict[str, str]) -> dict[Path, str]:
    cursor_rule = (
        "---\ndescription: OpenSurgicalVision Global AI Guidelines\nglobs: *\n---\n\n"
        "<!-- AUTO-GENERATED from .ai/context.md DO NOT EDIT DIRECTLY -->\n\n"
        + context
        + "\n\n## Autonomous Agents in CI\n"
        "The following agents operate asynchronously on this repository. Do not duplicate their work:\n\n"
        + "\n".join(f"- **{name}**: {parse_agent_description(body)}" for name, body in agents.items())
        + "\n"
    )
    return {ROOT_DIR / ".cursor" / "rules" / "osv-rules.mdc": cursor_rule}


def generate_copilot_instructions(context: str, agents: dict[str, str]) -> dict[Path, str]:
    copilot = (
        "<!-- AUTO-GENERATED from .ai/context.md DO NOT EDIT DIRECTLY -->\n\n"
        + context
        + "\n\n## Autonomous Agents in CI\n"
        "The following agents operate asynchronously on this repository. Do not duplicate their work:\n\n"
        + "\n".join(f"- **{name}**: {parse_agent_description(body)}" for name, body in agents.items())
        + "\n"
    )
    return {ROOT_DIR / ".github" / "copilot-instructions.md": copilot}


def generate_aider_conf(mcp_data: dict) -> dict[Path, str]:
    aider_conf = (
        "# AUTO-GENERATED from .ai/context.md\n"
        "read: .ai/context.md\n"
        "auto-commits: false\n"
        "attribute-author: true\n"
        "attribute-committer: true\n"
    )
    return {ROOT_DIR / ".aider.conf.yml": aider_conf}


def collect_all_generated() -> dict[Path, str]:
    context = load_context()
    mcp_data = load_mcp()
    skills = load_skills()
    commands = load_commands()
    hooks = load_hooks()
    agents = load_agents()

    all_files: dict[Path, str] = {}
    all_files.update(generate_claude(context, mcp_data, skills, commands, hooks, agents))
    all_files.update(generate_agents_md(context, skills, agents))
    all_files.update(generate_cursor_rules(context, agents))
    all_files.update(generate_copilot_instructions(context, agents))
    all_files.update(generate_aider_conf(mcp_data))
    return all_files


# Directories build() fully owns: every file in them is generated, so a file
# that exists here but is no longer in all_files is a stale leftover from a
# rename or deletion in .ai/ (this is exactly what happened once already: a
# generated agent file was left behind after its source in .ai/agents/ was
# renamed) and must be removed, not just never-updated-again.
MANAGED_DIRS = (
    ROOT_DIR / ".claude" / "agents",
    ROOT_DIR / ".claude" / "skills",
    ROOT_DIR / ".claude" / "commands",
    ROOT_DIR / ".claude" / "hooks",
)


def prune_stale_generated(all_files: dict[Path, str]) -> list[Path]:
    expected = set(all_files.keys())
    removed = []
    for directory in MANAGED_DIRS:
        if not directory.exists():
            continue
        for existing in directory.glob("*"):
            if existing.is_file() and existing not in expected:
                existing.unlink()
                removed.append(existing)
    return removed


def build() -> None:
    all_files = collect_all_generated()
    for path, content in all_files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        # Normalize newlines
        norm_content = content.replace("\r\n", "\n")
        path.write_text(norm_content, encoding="utf-8", newline="\n")
        print(f"Generated: {path.relative_to(ROOT_DIR)}")
    removed = prune_stale_generated(all_files)
    for path in removed:
        print(f"Removed (stale): {path.relative_to(ROOT_DIR)}")
    print(f"\n[OK] Successfully synchronized {len(all_files)} AI configuration files.")


def parse_agent_tools(content: str) -> str:
    """Pull the raw `tools:` line out of an agent's frontmatter, same
    line-scan approach as parse_agent_description (see its docstring)."""
    if not content.startswith("---"):
        return ""
    end = content.find("\n---", 3)
    frontmatter = content[3:end] if end != -1 else content[3:400]
    for line in frontmatter.splitlines():
        if line.strip().startswith("tools:"):
            return line.split(":", 1)[1].strip()
    return ""


def parse_agent_model(content: str) -> str:
    if not content.startswith("---"):
        return ""
    end = content.find("\n---", 3)
    frontmatter = content[3:end] if end != -1 else content[3:400]
    for line in frontmatter.splitlines():
        if line.strip().startswith("model:"):
            return line.split(":", 1)[1].strip()
    return ""


def check_no_bash_for_restricted_agents(agents: dict[str, str]) -> list[str]:
    """R-21: deid-gate, pr-triage, and newcomer-greeter read untrusted PR
    content and must never hold a general-purpose shell. This is what makes
    that a mechanically enforced rule instead of a paragraph someone has to
    remember to re-check on every future edit to these three files."""
    problems = []
    for name in NO_BASH_AGENTS:
        content = agents.get(name)
        if content is None:
            problems.append(f"R-21: expected agent '{name}' not found in .ai/agents/")
            continue
        tools = parse_agent_tools(content)
        tool_names = {t.strip() for t in tools.split(",")}
        if "Bash" in tool_names:
            problems.append(
                f"R-21 violation: .ai/agents/{name}.md grants Bash, but this agent reads "
                "untrusted PR content and must use osv-github-ro/osv-github-triage MCP tools "
                "instead. See docs/open-source-project-plan.md Sec. 5.11."
            )
    return problems


def check_model_pins(agents: dict[str, str]) -> list[str]:
    """R-22: every agent's `model:` field must be a literal ID present in
    .ai/models.json, never a floating tier alias like `sonnet` or `latest`.
    Approving a new model or bumping an existing one is a reviewed PR against
    that file, not a silent drift when a provider ships a new release."""
    if not MODELS_FILE.exists():
        return [f"R-22: {MODELS_FILE.relative_to(ROOT_DIR)} is missing."]
    approved = json.loads(MODELS_FILE.read_text(encoding="utf-8")).get("approved_models", {})
    problems = []
    for name, content in agents.items():
        model = parse_agent_model(content)
        if not model:
            problems.append(f"R-22 violation: .ai/agents/{name}.md has no `model:` field.")
        elif model not in approved:
            problems.append(
                f"R-22 violation: .ai/agents/{name}.md pins model '{model}', which is not in "
                f"the approved allowlist in {MODELS_FILE.relative_to(ROOT_DIR)}: {sorted(approved)}."
            )
    return problems


def check_all_hooks_registered() -> list[str]:
    """A hook file that exists but is wired to no event enforces nothing.

    This is the failure mode a guard has when it is added under deadline: the
    script lands in .ai/hooks/, gets copied to .claude/hooks/, and never runs,
    which looks identical to a working guard right up until it matters. Every
    .ai/hooks/*.py must appear in build_hook_config()."""
    registered = {
        entry["hooks"][0]["command"].rsplit("/", 1)[-1]
        for entries in build_hook_config().values()
        for entry in entries
    }
    problems = []
    for name in sorted(load_hooks()):
        if name not in registered:
            problems.append(
                f"Unregistered hook: .ai/hooks/{name} is not wired to any event in "
                "build_hook_config(). A hook that never fires is decoration."
            )
    return problems


def check_demo_allowlist() -> list[str]:
    """R-26: `demo_guard` refuses any frame that is not in demo-assets/allowlist.yaml.

    If the allowlist file is missing, the guard blocks every render, which is the
    safe direction but a confusing one to debug. Fail the check here instead, with
    the reason stated."""
    if not (HOOKS_DIR / "demo_guard.py").exists():
        return []
    allowlist = ROOT_DIR / "demo-assets" / "allowlist.yaml"
    if not allowlist.exists():
        return [
            "R-26: demo_guard.py is present but demo-assets/allowlist.yaml is missing. "
            "The allowlist is the only source of frames a demo clip may contain; without "
            "it every render is blocked."
        ]
    return []


def check() -> bool:
    all_files = collect_all_generated()
    mismatches = []
    for path, expected_content in all_files.items():
        if not path.exists():
            mismatches.append(f"Missing file: {path.relative_to(ROOT_DIR)}")
            continue
        current_content = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        exp_norm = expected_content.replace("\r\n", "\n")
        if current_content != exp_norm:
            mismatches.append(f"Content mismatch in: {path.relative_to(ROOT_DIR)}")

    agents = load_agents()
    mismatches += check_no_bash_for_restricted_agents(agents)
    mismatches += check_model_pins(agents)
    mismatches += check_all_hooks_registered()
    mismatches += check_demo_allowlist()

    if mismatches:
        print("[FAIL] AI configuration checks failed:")
        for m in mismatches:
            print(f"  - {m}")
        print("\nIf this is a sync issue, run 'python .ai/build.py' or 'make setup-ai'.")
        return False

    print(f"[PASS] All {len(all_files)} AI configuration files are in sync with .ai/ source.")
    print(f"[PASS] R-21 (no Bash for {', '.join(sorted(NO_BASH_AGENTS))}) holds.")
    print(f"[PASS] R-22 (model pins match {MODELS_FILE.relative_to(ROOT_DIR)}) holds.")
    print(f"[PASS] All {len(load_hooks())} hooks in .ai/hooks/ are wired to an event.")
    print("[PASS] R-26 (demo frame allowlist present) holds.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and check OSV AI configs.")
    parser.add_argument("--check", action="store_true", help="Verify if configs are in sync")
    args = parser.parse_args()

    if args.check:
        return 0 if check() else 1
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
