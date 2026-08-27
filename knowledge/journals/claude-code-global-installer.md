---
okf_version: "0.2"
type: Engineering Journal
title: "Claude Code global installer"
description: "Authoritative, verified user-scope MCP setup for Claude Code."
tags: [engineering, clients, onboarding]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-27T03:49:00Z
---

# Goal

Configure the MCP server in the Claude Code user registry that the CLI actually reads, without overwriting user-managed settings.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-27 - Implementation and verification

Global Claude Code setup now uses `~/.claude.json` and reports its execution method in previews. When available, the official Claude CLI adds, validates, and removes the exact user-scope entry. When it is unavailable, the installer atomically merges the documented top-level `mcpServers` entry and validates it locally. Conflicting or malformed canonical entries are preserved and skipped. The adapter recognizes Claude CLI's equivalent `stdio`/empty-environment representation so repeat setup and exact cleanup remain stable. The obsolete `~/.claude/mcp.json` is never altered; an exact stale managed entry receives a non-blocking diagnostic.

# Decisions

- Treat a present-but-failing Claude CLI as authoritative; do not hide its failure with a direct-write fallback.
- Preserve same-name entries that differ from the managed command.
- Keep portable project `.mcp.json` behavior unchanged.

# Testing

- `uv run ruff check src tests && uv run mypy src && uv run pytest -q` — passed (157 passed, 8 skipped).
- `bash scripts/e2e-user-journey.sh` — passed using the actual Claude CLI and an isolated temporary home.
- `./validate-okf` and `git diff --check` — passed.

# Open Issues

- None.

# References

- [Global client reliability and Cline synchronization](global-client-reliability.md)
- [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp)
