#!/usr/bin/env python3
"""PreToolUse guard for Bash.

Enforces R-06 (no verification bypass, no force-push to main), R-07 (allowlisted
egress) and R-12 (secrets never printed).

Contract: reads the hook payload as JSON on stdin. Exit 0 allows, exit 2 blocks.
"""

from __future__ import annotations

import json
import re
import sys

# (pattern, rule, explanation)
FORBIDDEN: list[tuple[str, str, str]] = [
    (
        r"--no-verify\b",
        "R-06",
        "Hooks exist because PHI leaks are irreversible. Fix the failing check instead.",
    ),
    (
        r"--no-gpg-sign\b",
        "R-06",
        "Commit signing is not optional in this project.",
    ),
    (
        r"git\s+push\b.*(--force|-f)\b(?!.*--force-with-lease)",
        "R-06",
        "Force-push rewrites shared history. Use --force-with-lease on your own branch, never on main.",
    ),
    (
        r"git\s+push\b.*\borigin\s+(main|master)\b",
        "R-10",
        "Direct pushes to main are forbidden. Open an MR.",
    ),
    (
        r"\b(printenv|env)\b(?!\s*\|)",
        "R-12",
        "Dumping the environment risks printing secrets into a transcript or a public log.",
    ),
    (
        r"echo\s+.*\$\{?(ANTHROPIC|OPENAI|HF|GITHUB|GITLAB|AWS|AZURE)_?[A-Z_]*(TOKEN|KEY|SECRET)",
        "R-12",
        "Never echo a credential.",
    ),
    (
        r"\brm\s+-rf\s+[/~]\s*$",
        "R-06",
        "Refusing an unbounded recursive delete.",
    ),
]

# R-07: egress allowlist. Anything else needs a human.
ALLOWED_HOSTS = (
    "git.epam.com",  # the project's actual git remote (GitLab, self-managed)
    "huggingface.co", "cdn-lfs.huggingface.co",
    "arxiv.org", "export.arxiv.org", "eutils.ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov",
    "pypi.org", "files.pythonhosted.org",
    "github.com", "api.github.com",  # runpod/runpod-plugins-official marketplace
    "registry.npmjs.org",  # npx @runpod/mcp-server, npx skills add
    "mcp.getrunpod.io",  # RunPod MCP OAuth
    # Shipping training code to a GPU pod. Deliberately the proxy host and not a
    # pod IP: pod addresses are per-pod and ephemeral, so allowlisting those
    # would amount to allowlisting any address RunPod happens to hand out.
    "ssh.runpod.io",
    "localhost", "127.0.0.1",
)

# Commands that leave the machine. `ssh`/`scp`/`sftp`/`rsync` are here because
# a guard that only inspects curl and wget is not an egress policy: pushing a
# tarball to an arbitrary host over scp exfiltrates exactly as well, and until
# this line existed those commands were never host-checked at all.
NETWORK_CMD = re.compile(r"\b(curl|wget|https?|ssh|scp|sftp|rsync)\b", re.IGNORECASE)
URL = re.compile(r"https?://([A-Za-z0-9.\-]+)")
# `scp file user@host:/path`, `ssh user@host`, `rsync -a dir host:/path`.
SSH_TARGET = re.compile(r"(?:^|\s)(?:[A-Za-z0-9._%+-]+@)([A-Za-z0-9.\-]+)")


def hosts_in(command: str) -> set[str]:
    return set(URL.findall(command)) | set(SSH_TARGET.findall(command))


def block(rule: str, command: str, why: str) -> None:
    print(f"BLOCKED by {rule}: {why}\nCommand: {command.strip()[:300]}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command", "")
    if not command:
        sys.exit(0)

    for pattern, rule, why in FORBIDDEN:
        if re.search(pattern, command, re.IGNORECASE):
            block(rule, command, why)

    if NETWORK_CMD.search(command):
        for host in sorted(hosts_in(command)):
            if not any(host == a or host.endswith("." + a) for a in ALLOWED_HOSTS):
                block(
                    "R-07",
                    command,
                    f"'{host}' is not on the egress allowlist. Exfiltration through generated\n"
                    "commands is the main prompt-injection payload; ask a human to widen the list.",
                )

    sys.exit(0)


if __name__ == "__main__":
    main()
