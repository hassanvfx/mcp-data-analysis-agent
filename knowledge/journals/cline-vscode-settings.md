---
type: Engineering Journal
title: "Cline VS Code settings target"
description: "Use the Cline extension's visible macOS VS Code MCP settings file for global setup."
tags: [engineering, clients, onboarding]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-25T22:40:00Z
---

# Goal

Configure Cline through the macOS VS Code extension settings file it actually reads, with a credential-free entry and reload guidance.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-25 22:25 - Initial context

The existing Cline adapter writes `~/.cline/mcp.json`, while the installed macOS VS Code extension reads its global-storage settings file. The visible extension target must become authoritative when present.

## 2026-08-25 22:40 - Implementation and verification

Global Cline setup now prefers the macOS VS Code extension settings target when extension storage exists, falls back to `~/.cline/mcp.json` otherwise, replaces only the stale `data-analysis-agent` key, validates every written client configuration, and emits Cline reload guidance with the exact target path. The hermetic macOS journey verified the target, migration, credential-free entry, and cleanup.

# Decisions

- Prefer the Cline VS Code global-storage target on macOS when its extension storage exists; otherwise retain the historical fallback.
- Replace only the known stale `data-analysis-agent` key during the Cline migration and preserve all other settings.

# Testing

Focused adapter/CLI tests and the hermetic journey passed. Final verification passed: 126 tests, 8 skipped; 91.00% line and 86.03% branch coverage; coverage gate, Ruff, mypy, shell syntax, OKF, and whitespace validation.

# Open Issues

None.

# References

- [Operational README replacement](operational-readme.md)
- [Full MCP removal](full-mcp-removal.md)
