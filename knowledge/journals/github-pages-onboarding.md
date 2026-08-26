---
okf_version: "0.2"
type: Engineering Journal
title: "GitHub Pages onboarding guide"
description: "URL-based agent handoff and hosted onboarding documentation."
tags: [engineering, documentation, onboarding]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-26T04:38:04Z
---

# Goal

Make the public installation handoff URL-specific and publish the detailed, safe project-onboarding workflow through GitHub Pages.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-25 - Initial context

The README currently contains the ambiguous phrase “Please install from repo.” and no Pages deployment exists. The implementation will make the README a concise handoff, add a dependency-free hosted guide, direct installer output to it, and keep the Codex acceptance prompt aligned.

## 2026-08-26 - Completed implementation

Replaced the README with a concise URL-based handoff and linked it to a static Pages guide. Added a Pages-only GitHub Actions deployment workflow, installer success guidance, documentation contracts, and the updated Codex handoff phrase. The guide explains the install-once/project-by-project model, manual source configuration, deterministic demo, governed queries, readiness states, client fallback, Cline reload behavior, cleanup, and supported SQLite/PostgreSQL dialects.

# Decisions

- Use the repository’s default project Pages URL and GitHub Actions deployment without a custom domain or site generator.
- Keep the README concise and use the hosted guide as the canonical detailed workflow.

# Testing

- `uv run pytest -q tests/test_documentation_contract.py tests/test_codex_handoff_script.py` — passed (11 tests).
- `uv run ruff check src tests && uv run mypy src && uv run pytest --cov=mcp_data_agent --cov-branch --cov-report=json:coverage.json && uv run python scripts/check_coverage.py coverage.json && ./validate-okf && git diff --check` — passed (130 passed, 8 skipped; 91.00% line, 86.03% branch coverage).
- `bash scripts/e2e-user-journey.sh` — passed with isolated setup and teardown.
- Parsed the Pages workflow YAML and confirmed the static site references and handoff phrase.

# Open Issues

- GitHub Pages must be configured to use GitHub Actions in repository settings before the first public deployment.

# References

- [Operational README replacement](operational-readme.md)
- [Codex agent-handoff acceptance](codex-handoff-acceptance.md)
