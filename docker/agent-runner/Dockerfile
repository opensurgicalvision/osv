# Container for Stage B: the LLM agent (deid-gate, pr-triage, newcomer-greeter)
# runs inside this image with the host filesystem mounted READ-ONLY and only
# /tmp writable, on top of -- not instead of -- the tool-level restrictions in
# .ai/agents/*.md (no Bash, MCP-only GitHub access, label allowlist). Defense
# in depth: even if every application-level guard were somehow talked around,
# `docker run --read-only` means a write attempt hits a read-only filesystem
# error, not a modified file. See docs/open-source-project-plan.md Sec. 5.11.
#
# Network is NOT restricted here -- the agent needs egress to the Anthropic
# API and the osv-github-ro/osv-github-triage MCP servers need it for the
# GitHub API, so a read-only root filesystem is this image's actual security
# property, not network isolation. Do not represent this image as sandboxing
# network access; it does not.
#
# Build:  docker build -t osv-agent-runner -f docker/agent-runner/Dockerfile .
# Run:    docker run --rm --read-only --tmpfs /tmp:rw,size=256m \
#           -v "$PWD:/workspace:ro" -w /workspace \
#           -e ANTHROPIC_API_KEY -e GITHUB_TOKEN \
#           osv-agent-runner claude -p "..."
#
# NOTE: the exact `claude` CLI invocation (flags for headless mode, selecting
# a named subagent) depends on the installed Claude Code CLI version. Verify
# against your version before wiring this into ai-stage-b.yml.

FROM node:20-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    NPM_CONFIG_UPDATE_NOTIFIER=false

# python3 + uv: the osv-github-ro / osv-github-triage MCP servers are Python
# scripts launched via `uv run` (see .ai/mcp/servers.json). No `curl`/`wget`
# is added beyond what the base image and pip/npm installers themselves need
# -- this image is not a general-purpose shell environment.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --break-system-packages uv

# Official Claude Code CLI.
RUN npm install -g @anthropic-ai/claude-code && npm cache clean --force

WORKDIR /workspace

# No CMD/ENTRYPOINT that runs anything by default -- the invoking workflow
# passes the exact `claude -p ...` command explicitly at `docker run` time.
