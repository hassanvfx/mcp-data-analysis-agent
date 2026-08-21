# Working with ChatGPT Codex

ClineFlow gives ChatGPT Codex persistent project context through the repository's shared `AGENTS.md` instructions and the native OKF bundle in `knowledge/`. It does not require a Codex plugin, SDK, or runtime.

## Start or resume a task

1. Read `AGENTS.md` and `knowledge/index.md`.
2. Search `knowledge/` for relevant concepts. When present, search `docs/journals/` as read-only legacy context too.
3. Summarize the relevant context before changing code. For a substantial change, propose a concise implementation plan first.
4. Create or resume `knowledge/journals/<task-name>.md` from `knowledge/journals/TASK_TEMPLATE.md`.

## Work and deliver

- Keep the active Engineering Journal current with decisions, implementation notes, verification evidence, issues, and next steps.
- Link related knowledge with normal Markdown links and update `knowledge/log.md` when the knowledge changed materially.
- Before a delivery or commit, run `./validate-okf`, the relevant project tests, and `git diff --check`.
- When the user asks to commit, update the journal and log first, then commit the code and knowledge artifacts together.

## Useful prompts for Codex

**Start work**

> Read `AGENTS.md` and `knowledge/index.md`, search relevant journals, summarize the current context, and propose the next safe step.

**Resume work**

> Find the active Engineering Journal in `knowledge/journals/`, inspect its next steps and related knowledge, then continue from the documented state.

**Close a task**

> Update the active Engineering Journal with decisions and verification evidence, update `knowledge/log.md` if needed, run `./validate-okf` and relevant tests, then show me the delivery summary.

## Diagnose the setup

Run `./clineflow-doctor` after installation or when Codex does not appear to have project context. It checks the shared instructions, required OKF files, Git repository, and structural validation without installing anything. `./clineflow-doctor --strict` additionally uses strict YAML validation only when optional PyYAML is already available.
