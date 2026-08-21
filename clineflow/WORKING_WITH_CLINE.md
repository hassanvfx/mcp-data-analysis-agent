# Working with ClineFlow

ClineFlow stores new persistent context as an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) v0.2 bundle in `knowledge/`.

## Daily workflow

1. Ask the agent to inspect `knowledge/index.md` before starting work.
2. For a substantial task, create `knowledge/journals/<task-name>.md` from `knowledge/journals/TASK_TEMPLATE.md`.
3. Keep decisions, testing evidence, progress, and next steps in that concept.
4. At commit time, validate with `./validate-okf`, update `knowledge/log.md` when appropriate, and commit code plus knowledge together.

## Legacy journal discovery

Projects may have pre-OKF journals in `docs/journals/`. ClineFlow searches these files for historical context when they exist, but does not modify, migrate, or validate them. All new task documentation belongs in `knowledge/journals/`.

## Reference repositories

The optional symlink and multi-root-workspace reference system remains available. See `clineflow/README.md` and run `./setup-refs.sh --help`.
