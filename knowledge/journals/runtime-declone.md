---
type: Engineering Journal
title: "Runtime de-cloning of MCP operation"
description: "Remove ClineFlow and repository-bootstrap assumptions from installed MCP operation."
tags: [engineering, mcp, runtime, distribution]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-25T13:20:00Z
---

# Goal

Make the installed MCP operate in arbitrary projects with only project-local source configuration and observability records.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-25 02:00 UTC - Initial context

- Runtime preflight and doctor still require the active project to contain ClineFlow scripts and an OKF bundle.
- Task lifecycle creates ClineFlow journals beside observability records, and context APIs expose project knowledge files.
- These assumptions conflict with the global credential-free MCP installation model.

## 2026-08-25 13:05 UTC - Runtime decoupling completed

- Removed the installed-package ClineFlow context API and module, task-journal creation/completion, task `journal` frontmatter, and `TaskResult.journal_path`.
- Simplified preflight and doctor to source/project/MCP-executable operational checks; they no longer run ClineFlow checks, inspect Git, synchronize `uv`, or install Typst/PostgreSQL tooling.
- Kept the repository's own ClineFlow/OKF contributor workflow while documenting that it is never invoked in arbitrary user projects.
- Reclassified Typst as a PDF-only optional renderer and PostgreSQL command-line tools as contributor/test tooling.
- Removed the obsolete policy `env` field and test fixtures so `.mcp-data-source` remains the only operational source configuration, apart from the explicit legacy migration command.
- Updated user-facing installation, operations, specification, goal, tests, and coverage gates for the observability-only user-project contract.

# Decisions

- Keep ClineFlow and OKF as repository-development workflow only; remove all installed-package runtime coupling.
- Retain project-local observability records as the complete task audit trail.

# Testing

- `uv run ruff check src tests` - passed.
- `uv run mypy src` - passed.
- `uv run pytest --cov=mcp_data_agent --cov-branch --cov-report=json:coverage.json` - passed: 97 passed, 8 skipped; 91.81% line and 85.11% branch coverage.
- `uv run python scripts/check_coverage.py coverage.json` - passed; configuration, ledger, and policy remain 100% line/branch covered.
- `./validate-okf` and `git diff --check` - passed.
- Manual CLI check: a fresh unconfigured directory reported `source_configuration_required`; a separate fresh directory configured with `configure-source --fixture --yes` passed preflight and returned the fixture schema. Neither project required or created `knowledge/`.

# Open Issues

None.

# References

- [Per-project source configuration](per-project-source-configuration.md)
- [Delivery goal](mcp-data-analysis-agent-goal.md)
