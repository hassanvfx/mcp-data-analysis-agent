---
type: Engineering Journal
title: "Full MCP removal"
description: "Confirmation-gated removal of managed MCP entries, tool installation, demo fixtures, and local editable checkout."
tags: [engineering, onboarding, cleanup]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-25T22:05:00Z
---

# Goal

Implement a full, previewable MCP Data Analysis removal flow across supported global clients and explicit project roots.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-25 21:35 - Initial context

The existing cleanup removes exact global client entries and optionally the current project demo, but leaves project fallback entries, the uv tool environment, and local editable checkout removal to manual work. The requested full flow must preserve unrelated configuration and never discover projects by scanning the disk.

## 2026-08-25 22:05 - Implementation and verification

Added previewable `uninstall --all` with repeatable explicit project roots, exact global/project client removal, guarded managed-demo cleanup, uv-tool removal, and validated delayed editable-checkout deletion. The current editable checkout is only selected from the running package layout; package/remote installations report no local checkout. The installer is executable, matching the documented local command.

# Decisions

- Full removal targets all supported global clients plus the current project and explicitly supplied absolute project roots.
- Managed demos are removed; custom sources and governance/evidence are preserved.
- A validated editable checkout is deleted after the running CLI exits, including dirty worktrees, as explicitly requested.

# Testing

The targeted removal and interface tests passed. The hermetic editable-install-to-full-removal journey passed. Final verification passed: 123 tests, 8 skipped; 91.24% line and 86.34% branch coverage; coverage gate, Ruff, mypy, shell syntax, OKF, and whitespace validation.

# Open Issues

None.

# References

- [Codex agent-handoff acceptance](codex-handoff-acceptance.md)
- [Operational README replacement](operational-readme.md)
