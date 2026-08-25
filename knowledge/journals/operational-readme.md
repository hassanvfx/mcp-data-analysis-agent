---
type: Engineering Journal
title: "Operational README replacement"
description: "Replace legacy onboarding documentation with the current install, source, analysis, and cleanup contract."
tags: [engineering, documentation, onboarding]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-25T19:41:00Z
---

# Goal

Create an operation-first public README and explicitly deprecate legacy bootstrap documentation.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-25 19:36 UTC - Documentation replacement started

- Replaced the top-level README with the current credential-free global installation and project-local source lifecycle.
- Added an explicit agent-install instruction for the public repository and cloned checkouts.
- Added a legacy-documentation notice rather than presenting historical bootstrap behavior as current operation.

# Decisions

- The README is the canonical user/operator guide; the legacy notice directs historical investigation to repository history and dated knowledge records.

# Testing

- `git diff --check`, `./validate-okf`, `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q` passed.

# Open Issues

None.

# References

- [Journey hardening implementation](journey-hardening-implementation.md)
- [Runtime de-cloning](runtime-declone.md)
