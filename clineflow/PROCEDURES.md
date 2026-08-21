# ClineFlow Procedures

## Start or resume work

1. Read `knowledge/index.md` and the relevant concept indexes.
2. Search `knowledge/` for related task journals, decisions, and references.
3. When present, search `docs/journals/` for relevant legacy context. Treat these files as read-only historical material.
4. Create or resume `knowledge/journals/<task-name>.md` from `knowledge/journals/TASK_TEMPLATE.md` for substantial work.

## Maintain OKF knowledge

- Keep every non-reserved Markdown document in `knowledge/` parseable with YAML frontmatter and a non-empty `type`.
- Reserve `index.md` for navigation and `log.md` for dated change history.
- Use Markdown links for relationships; broken links are acceptable when knowledge is not written yet.
- Record only factual provenance, verification, and lifecycle fields.

## Commit

1. Update the active Engineering Journal with outcomes, decisions, tests, and follow-up work.
2. Add a dated entry to `knowledge/log.md` for material changes.
3. Run `./validate-okf`.
4. Commit implementation and knowledge changes together.
