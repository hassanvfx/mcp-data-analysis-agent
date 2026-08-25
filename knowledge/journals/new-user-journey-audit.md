---
type: Engineering Journal
title: "New-user demo and customization journey audit"
description: "Audit the clone, demo, and source-customization path for the global MCP product."
tags: [engineering, onboarding, mcp, usability]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-25T14:05:00Z
---

# Goal

Identify friction and missing adaptation work in the new-user journey from repository clone through demo configuration and real-source customization.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-25 13:30 UTC - Initial context

- The product has moved to a credential-free global MCP installation with explicit per-project source configuration and opt-in demo setup.
- This audit evaluates the resulting public journey and identifies remaining user-facing gaps without changing implementation.

## 2026-08-25 14:05 UTC - Findings

- A clone followed by `./install.sh` installs the remote Git repository rather than the checked-out code. The public guidance lacks a distinct clone/developer quickstart.
- `.mcp-data-source` and `.mcp-data/` are ignored in this repository, but `configure-source` does not add their rules to an arbitrary user project's `.gitignore`. A credential-bearing PostgreSQL URL can therefore be accidentally committed.
- `preflight` reports `ready` for a syntactically valid but nonexistent SQLite path; it validates configuration only and does not state that it has not checked connectivity or read-only access.
- `mcp-data-cli demo start` creates a fixture but does not configure `.mcp-data-source`, while `configure-source --fixture` does. The two demo paths overlap and have different outcomes.
- The global-client working-directory contract remains unproven for every supported client. The server must start in the active project for its relative source-file argument to resolve correctly.
- New users can begin querying the fixture immediately, but there is no confirmation-gated scaffold for optional policy, catalog, or recipe files when they move to a real source.

# Decisions

- Evaluate both a user who clones the repository and a user who installs the package into an unrelated data project.
- Keep global client entries credential-free; any improvement to Git ignores or policy scaffolding must remain optional and confirmation-gated.

# Testing

- Inspected the public install/source/demo workflow in `README.md`, `docs/OPERATIONS.md`, `install.sh`, `onboarding.py`, and client setup code.
- Temporary-project check: an absolute nonexistent SQLite path passed `mcp-data-cli preflight` as `ready`, confirming that source-file validation is not a connection probe.
- CLI help check: `demo start` and `configure-source --fixture` expose distinct, overlapping fixture paths.

# Open Issues

1. Add a concise **Use after clone** and **Use in an existing project** quickstart, including the exact demo-to-real-source transition.
2. Add confirmation-gated Git-ignore assistance or a clear no-Git fallback warning for `.mcp-data-source` and `.mcp-data/`.
3. Rename preflight status to configuration-ready or add an explicit opt-in connection/read-only probe.
4. Consolidate demo behavior so every advertised demo command makes the fixture usable, or clearly reserve `demo` for contributor fixture generation.
5. Run a client-by-client working-directory smoke matrix after global installation, especially for Codex, Claude Code, Copilot, Cline, Cursor, Windsurf, and Continue.
6. Consider an optional policy/catalog/recipe scaffold after the user has inspected a real source.

# References

- [Per-project source configuration](per-project-source-configuration.md)
- [Runtime de-cloning](runtime-declone.md)
- [README](../../README.md)
- [Operations guide](../../docs/OPERATIONS.md)
