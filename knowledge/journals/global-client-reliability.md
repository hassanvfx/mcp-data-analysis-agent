---
okf_version: "0.2"
type: Engineering Journal
title: "Global client reliability and Cline synchronization"
description: "Absolute global MCP commands and synchronized Cline runtime configuration."
tags: [engineering, clients, onboarding]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-26T04:59:58Z
---

# Goal

Make every global MCP client entry launch a verified absolute executable and synchronize all recognized Cline runtime settings files without storing database credentials.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-26 - Initial context

Cline can select either VS Code extension storage or native Cline settings at runtime. The previous installer wrote only one target and used a PATH-dependent command. This change synchronizes known existing targets, resolves an absolute installed executable for global clients, retains portable project entries, and documents safe agentic removal.

## 2026-08-26 - Implementation and verification

Global setup now resolves a validated absolute `mcp-data-mcp` command through the installed `uv` tool bin, explicit override, or PATH fallback and applies it to every supported global client format. The installer passes the just-installed command explicitly. Cline synchronizes existing VS Code, native, and historical settings independently, removes only the known legacy server key, reports every target, and retains portable project entries. Documentation now includes the preview-first “Please uninstall MCP Data Analysis from all agents” handoff.

# Decisions

- Apply absolute executable paths to every global client entry; keep project entries portable.
- Synchronize existing VS Code, native Cline, and historical Cline files; explicitly create only native Cline settings when no runtime target exists.

# Testing

- `uv run ruff check src tests && uv run mypy src && uv run pytest -q tests/test_interfaces.py tests/test_install_script.py tests/test_codex_handoff_script.py tests/test_documentation_contract.py` — passed.
- `bash scripts/e2e-user-journey.sh` — passed with VS Code/native Cline synchronization, absolute global commands, and full cleanup.
- `uv run pytest --cov=mcp_data_agent --cov-branch --cov-report=json:coverage.json && uv run python scripts/check_coverage.py coverage.json && ./validate-okf && git diff --check` — passed (134 passed, 8 skipped; 91.05% line and 85.80% branch coverage).

# Open Issues

- None.

# References

- [Cline VS Code settings target](cline-vscode-settings.md)
- [Full MCP removal](full-mcp-removal.md)
