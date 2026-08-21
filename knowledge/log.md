# Knowledge Update Log

## 2026-08-21

* **MCP Data Analysis Agent specification**: Added and expanded the stable [local MCP product specification](journals/mcp-data-analysis-agent-spec.md), covering ClineFlow-backed project memory, one-line local installation and preflight, human-controlled credential onboarding, secure SQLite/PostgreSQL analytics, structured observability, reports, development fixtures, acceptance criteria, and safe failure behavior.
* **MCP Data Analysis Agent delivery goal**: Added the active [delivery goal journal](journals/mcp-data-analysis-agent-goal.md), separating implementation milestones and completion evidence from the stable product specification.
* **Representative analytics scenarios**: Added linked retail, SaaS, and support use cases to the stable [specification](journals/mcp-data-analysis-agent-spec.md) and active [delivery goal](journals/mcp-data-analysis-agent-goal.md), defining deterministic synthetic data, expected evidence, and test verification.

* **Implementation checkpoint**: Added the initial local MCP package, safe SQL/SQLite execution path, ClineFlow-linked observability ledger, multi-agent configuration templates, and deterministic retail/SaaS/support development fixtures. Verification evidence and remaining production-readiness work are recorded in the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Report and policy checkpoint**: Added table/schema policy enforcement, governed explain/profile/recipe/timeline operations, and safe HTML/CSV/Parquet/optional-PDF report outputs. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md) for verification evidence.

* **Full-domain fixture checkpoint**: Expanded deterministic development fixtures to represent all documented retail, SaaS, and support relationships used by the six target scenarios. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md) for the tested evidence.

* **Six golden workflow checkpoint**: Added fixture-backed, governed golden queries for all six retail, SaaS, and support delivery scenarios. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md) for results.

* **Task evaluation checkpoint**: Task completion now closes linked ClineFlow journals and a deterministic evaluator assesses lifecycle receipt completeness. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md) for validation evidence.

* **Interface coverage checkpoint**: Added direct MCP and fixture-backed CLI contract tests, raising measured coverage to 83% while identifying the remaining PostgreSQL and optional-renderer paths. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Safety coverage checkpoint**: Added adapter, SQL-policy, artifact, CLI, and MCP path coverage; the test suite now reaches 90% combined coverage. The separate branch-coverage gate remains documented as unfinished in the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **PostgreSQL CI parity checkpoint**: Added a disposable PostgreSQL 16 Actions service and an opt-in adapter contract test that stays locally safe by requiring an explicit disposable URL. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Observability integrity checkpoint**: Added immutable receipt and event-timeline verification with a tampering regression test, exposed to CLI and MCP users. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Receipt-backed report checkpoint**: Added receipt metadata and escaped evidence embedding to generated dashboards and exports. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Bounded execution checkpoint**: Added strict positive-limit enforcement, configured query concurrency bounds, and correlated failed-run ledger events. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Data-quality evidence checkpoint**: Added per-column null and freshness evidence to safe quality checks. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Period comparison checkpoint**: Added receipt-backed governed period comparisons and deterministic result change detection through CLI and MCP. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Schema drift checkpoint**: Added atomic local schema fingerprints and drift detection for safe discovery-cache invalidation. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **PostgreSQL schema isolation checkpoint**: Added configured schema search-path enforcement for unqualified PostgreSQL queries. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Observability retention correction**: Made durable audit ledger records Git-versionable while retaining exclusions for credentials, databases, caches, and generated artifacts. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Artifact path-safety checkpoint**: Hardened generated-output paths against symlink traversal. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **SQL bypass hardening checkpoint**: Blocked PostgreSQL `SELECT INTO` and targeted unsafe function bypasses in the read-only SQL policy. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

## YYYY-MM-DD

* **Initialization**: Created the ClineFlow OKF knowledge bundle.
