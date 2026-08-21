# ClineFlow: OKF Knowledge Workflow

This project keeps persistent engineering context in the `knowledge/` Open Knowledge Format (OKF) v0.2 bundle.

## ChatGPT Codex and compatible agents

`AGENTS.md` is the shared instruction entry point for ChatGPT Codex, Cursor, and other compatible coding agents. Read `clineflow/WORKING_WITH_CODEX.md` for the Codex workflow; the same OKF knowledge contract also applies to Cline, Copilot, and Windsurf.

## Task knowledge rules

1. For each substantial task, create or resume `knowledge/journals/<task-name>.md` using `knowledge/journals/TASK_TEMPLATE.md`.
2. Every task journal is an OKF concept. Keep its YAML frontmatter valid, retain `type: Engineering Journal`, and update `generated.at` after meaningful changes.
3. Use `status: draft` while work is active and `status: stable` when it is complete. Do not add `verified` or `sources` unless they are factual.
4. Before starting or resuming work, search `knowledge/` first. If `docs/journals/` exists, search it too as read-only legacy context. Never create or update new work there.
5. Link related concepts with normal Markdown links. Update `knowledge/log.md` for material knowledge changes.

## Commit workflow

When the user asks to commit:

1. Update the active `knowledge/journals/` concept with the implementation summary, decisions, tests, and next steps.
2. Update `knowledge/log.md` if the change added or materially changed knowledge.
3. Run `./validate-okf` and resolve validation failures. When the project has optional PyYAML available, prefer `./validate-okf --strict` before committing.
4. Stage the code and updated knowledge artifacts together, then create a descriptive commit.

## Knowledge navigation

- Start with `knowledge/index.md` and descend through `index.md` files for progressive disclosure.
- `docs/journals/` is optional legacy history; it is not part of the OKF bundle and must not be passed to `validate-okf`.
- The reference-repository system under `clineflow/` remains optional and unchanged.

## Code quality

- Prefer focused modules (roughly 300–500 lines; refactor files over 1,000 lines).
- Keep documentation concise, factual, and linked to the concepts or files it describes.
