---
type: Engineering Journal
title: "Operational README replacement"
description: "Replace legacy onboarding documentation with the current install, source, analysis, and cleanup contract."
tags: [engineering, documentation, onboarding]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-25T20:05:00Z
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

## 2026-08-25 20:05 UTC - Agent handoff simplification

- Reframed the README as the explicit user-to-agent middleware contract, with three short phrases: “Please install from repo,” “Please configure this folder,” and “Please install demo in this folder.”
- Documented the configuration handoff precisely: the agent prepares an empty private source file and opens the platform editor, while the user pastes and saves the one source value before the agent runs redacted preflight.
- Kept installation scope explicit: package installation configures a global credential-free MCP server; every data folder independently opts in.

# Decisions

- The README is the canonical user/operator guide; the legacy notice directs historical investigation to repository history and dated knowledge records.

# Testing

- `git diff --check` and `./validate-okf` passed after the handoff rewrite; no runtime code changed.

# Open Issues

None.

# References

- [Journey hardening implementation](journey-hardening-implementation.md)
- [Runtime de-cloning](runtime-declone.md)
