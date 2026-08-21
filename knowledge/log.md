# Knowledge Update Log

## 2026-08-21

* **SQLAlchemy Core adapter migration**: Created the active [migration journal](journals/sqlalchemy-core-adapter-migration.md) for portable SQLite/PostgreSQL data access and parity evidence.

* **SQLAlchemy Core engine migration checkpoint**: Migrated governed adapters and shared service execution to Core engines, connections, `text()`, and result APIs. See the [migration journal](journals/sqlalchemy-core-adapter-migration.md).

* **PostgreSQL Core contract checkpoint**: Expanded the disposable PostgreSQL CI contract for the new shared Core adapter behavior. See the [migration journal](journals/sqlalchemy-core-adapter-migration.md).

* **Local PostgreSQL parity checkpoint**: Added CLI-created, deterministic PostgreSQL fixtures and verified the SQLite/PostgreSQL Core contract against an isolated local server. See the [migration journal](journals/sqlalchemy-core-adapter-migration.md).

* **PostgreSQL session-enforcement checkpoint**: Verified live read-only session enforcement and server statement timeout behavior through the SQLAlchemy Core adapter. See the [migration journal](journals/sqlalchemy-core-adapter-migration.md).

* **Required Typst rendering checkpoint**: Verified the installed Typst compiler end-to-end and corrected report table syntax found by the real render. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

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

* **Recipe path-safety checkpoint**: Hardened Git-native recipe lookup against caller-supplied path traversal. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Enforced coverage-gate checkpoint**: CI now independently enforces the overall 90% statement and 85% branch thresholds, backed by expanded public-interface and failure-path tests. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Critical safety coverage checkpoint**: CI now requires 100% line and branch coverage for configuration, ClineFlow context, observability ledger, and SQL policy modules. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Pre-execution SQL validation checkpoint**: Added a safe SQL-validation CLI/MCP interface that returns policy evidence before source access. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Task-audit linkage checkpoint**: Task records now accumulate source, receipt, run, and artifact references as a complete audit index. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **MCP task-completion checkpoint**: Added the missing MCP task-completion lifecycle tool. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Package build checkpoint**: Built the source distribution and wheel and smoke-tested the declared CLI/MCP entry points. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Release and security automation checkpoint**: Added CI dependency audit/SBOM generation, a security policy, and an attested trusted-PyPI publishing workflow. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **End-to-end evidence checkpoint**: Added full governed evidence-chain tests for retail, SaaS, and support analysis tasks. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Data classification checkpoint**: Added validated field classifications, result metadata propagation, and restricted-field policy enforcement. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Wildcard restricted-field safety checkpoint**: Blocked wildcard projections when restricted fields are configured. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Wildcard projection precision checkpoint**: Preserved approved aggregate queries while enforcing restricted-field wildcard protection. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Auditable cancellation-request checkpoint**: Added pre-dispatch task cancellation with immutable cancellation evidence. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **SQLite in-flight cancellation and timeout checkpoint**: Added deterministic SQLite query interruption for running cancellation requests and elapsed deadlines. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **PostgreSQL typed timeout checkpoint**: Normalized server-side statement timeouts into the governed query result error model. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Approved recipe catalog checkpoint**: Added validated, versioned recipes for the three synthetic domains with CLI/MCP discovery. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Deterministic benchmark evidence checkpoint**: Added generated all-domain recipe/evidence performance coverage with a 60-second limit. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Governed semantic metric checkpoint**: Added approved revenue and MRR execution through the shared safe-query and receipt path. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Restricted source classification checkpoint**: Enforced source-level policy denial before parsing or connecting. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Source classification normalization checkpoint**: Closed the case-variant restricted-source policy bypass. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Transactional export cleanup checkpoint**: Failed report/export renders now leave no partial final output directory. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Safe preflight repair checkpoint**: Added idempotent non-secret template repair without touching private credentials or knowledge. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Installation-enforcing preflight checkpoint**: Default preflight now syncs required extras and provisions Typst through a non-privileged supported package manager. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Cross-platform installer coverage checkpoint**: Added deterministic Windows Typst installer coverage and raised global branch evidence. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

## YYYY-MM-DD

* **Initialization**: Created the ClineFlow OKF knowledge bundle.
