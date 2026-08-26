---
type: Engineering Journal
title: "Codex agent-handoff acceptance"
description: "Opt-in live Codex terminal-flow acceptance evidence with hermetic teardown."
tags: [engineering, acceptance, codex]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-25T21:22:00Z
---

# Goal

Add an opt-in live acceptance harness that proves Codex can follow the README handoff in an isolated project, while retaining the deterministic CLI journey as CI evidence.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-25 20:40 - Initial implementation

Added the isolated Codex handoff harness and extended cleanup markers. The harness uses an authenticated Codex invocation only when explicitly run, records redacted deterministic evidence externally, and removes its marked sibling sandbox on success, failure, or interruption.

# Decisions

- Keep live Codex usage opt-in and outside CI because it consumes the caller's authenticated model usage.
- Validate MCP configuration and CLI effects independently in shell; this intentionally does not claim a live MCP-tool call inside a caller profile.
- Store only the final-message SHA-256 and fixed evidence labels in the report, never paths, URLs, credentials, or transcripts.

# Testing

`bash -n scripts/e2e-codex-handoff.sh scripts/e2e-cleanup.sh` and the fake-Codex subprocess contract passed. The fake test covers successful evidence/cleanup plus nonzero and unavailable Codex failure reports without using model usage.

## 2026-08-25 21:00 - Completion audit

The pasted README acceptance contract is byte-identical to the active README. Local verification passed: 117 tests with 91.62% line and 86.10% branch coverage, the coverage gate, Ruff, mypy, shell syntax checks, OKF validation, and whitespace validation. The opt-in authenticated Codex execution remains pending explicit approval because it can transmit repository context to Codex and consume model usage.

## 2026-08-25 21:22 - Authorized live acceptance

The authorized `e2e-codex-handoff.sh` run passed. Its redacted external report records every expected phase: isolated setup and dependency cache, missing-source baseline, Codex handoff, source-repository integrity, static global entry, demo setup, ready preflight, `products` schema evidence, bounded query evidence, observability, and removed teardown. The direct live run also exposed and corrected two harness defects: unsupported Codex flags were replaced with current supported options, and the documented `./install.sh --local` path is now executable. An isolated dependency cache lets the agent run that exact installer while its workspace sandbox remains network-restricted.

# Open Issues

None.

# References

- [Operational README replacement](operational-readme.md)
- [New-user journey hardening](journey-hardening-implementation.md)
