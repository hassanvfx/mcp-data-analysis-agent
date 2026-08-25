---
type: Engineering Journal
title: "Per-project MCP source configuration"
description: "Replace ambient source URL configuration with an explicit project-local MCP source file."
tags: [engineering, mcp, configuration, security]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-25T01:15:00Z
---

# Goal

Make the globally installed MCP server credential-free and require an ignored `.mcp-data-source` file for every project that accesses a database.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-25 00:00 UTC - Initial context

- The prior implementation loaded `MCP_DATA_SOURCE_URL` from the active project's `.env` and silently generated a project fixture when absent.
- This task removes that ambient and cross-project configuration path. The source file becomes the only project database configuration; missing configuration must fail closed with actionable guidance.

## 2026-08-25 01:00 UTC - Delivery checkpoint

- Replaced runtime `.env` loading and automatic project playground selection with strict `.mcp-data-source` resolution. An explicit `--source-url` remains a diagnostic override; otherwise a missing source returns `SOURCE_CONFIGURATION_REQUIRED` with local setup guidance.
- Added global client entries that invoke `mcp-data-mcp --source-file .mcp-data-source`, a structured MCP `preflight` tool, and confirmation-gated `configure-source` CLI support for direct URLs, explicit fixtures, and one-time legacy `.env` migration.
- Removed dotenv from package dependencies and rewrote installation, operations, security, and public setup guidance around credential-free global installation plus project-local configuration.
- Added resolver, isolation, redaction, malformed-file, symlink, migration, preflight, and fixture tests. Existing analytical tests now supply their project source file explicitly.

## 2026-08-25 01:15 UTC - Demo setup handoff

- Missing-source MCP preflight now tells the agent to ask whether the user wants a seeded retail demo, rather than silently creating one.
- Added `configure_demo(confirmed=false)` to preview the exact project writes and `configure_demo(confirmed=true)` to generate the retail fixture, write `.mcp-data-source`, and return practical schema/query/task next steps.

# Decisions

- Source precedence is explicit `--source-url`, then `--source-file`, then a structured configuration-required error.
- The deterministic fixture is opt-in through a confirmation-gated CLI action that writes the project source file.

# Testing

- `uv run ruff check src tests scripts` — passed.
- `uv run mypy src` — passed.
- `uv run pytest --cov=mcp_data_agent --cov-branch --cov-report=json -q` — passed; 91.63% lines and 85.05% branches, with configuration/context/ledger/policy at 100% line and branch coverage.
- `uv run python scripts/check_coverage.py coverage.json`, `./validate-okf`, and `git diff --check` — passed.
- Demo-handoff validation: full suite passed at 91.68% lines and 85.13% branches.

# Open Issues

- Live client working-directory behavior must be manually verified after reinstalling/restarting the global MCP configuration; diagnostics expose source origin but never the URL.

# References

- [Delivery goal](mcp-data-analysis-agent-goal.md)
- [Simplified bootstrap journal](simplified-project-bootstrap.md)
