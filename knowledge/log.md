# Knowledge Update Log

## 2026-08-25

* **New-user journey hardening**: Added editable clone installation, live read-only source preflight, Git-ignore assistance, managed demo/policy/client cleanup, project-root client fallback, and hermetic install-to-teardown acceptance evidence. See the [implementation journal](journals/journey-hardening-implementation.md).

* **New-user journey audit**: Identified clone-install, Git-ignore, connectivity-status, overlapping-demo, client-working-directory, and optional-policy-scaffold follow-ups for the credential-free global MCP workflow. See the [new-user journey audit](journals/new-user-journey-audit.md).

* **Runtime de-cloning checkpoint**: Removed ClineFlow/OKF, Git, dependency-installation, and tooling prerequisites from installed MCP operation. User-project task evidence is now observability-only; Typst is PDF-only optional and PostgreSQL CLI tooling is contributor/test-only. See the [runtime de-cloning journal](journals/runtime-declone.md).

* **Per-project MCP source configuration checkpoint**: Replaced ambient `.env` source loading and automatic project fixtures with the ignored project-local `.mcp-data-source` contract, credential-free global client commands, required MCP preflight, and explicit source/fixture migration setup. See the [source-configuration journal](journals/per-project-source-configuration.md).

* **MCP demo handoff checkpoint**: Missing project configuration now offers a confirmation-gated seeded retail demo setup with practical next-step examples. See the [source-configuration journal](journals/per-project-source-configuration.md).

## 2026-08-21

* **SQLAlchemy Core adapter migration**: Created the active [migration journal](journals/sqlalchemy-core-adapter-migration.md) for portable SQLite/PostgreSQL data access and parity evidence.

* **SQLAlchemy Core engine migration checkpoint**: Migrated governed adapters and shared service execution to Core engines, connections, `text()`, and result APIs. See the [migration journal](journals/sqlalchemy-core-adapter-migration.md).

* **PostgreSQL Core contract checkpoint**: Expanded the disposable PostgreSQL CI contract for the new shared Core adapter behavior. See the [migration journal](journals/sqlalchemy-core-adapter-migration.md).

* **Local PostgreSQL parity checkpoint**: Added CLI-created, deterministic PostgreSQL fixtures and verified the SQLite/PostgreSQL Core contract against an isolated local server. See the [migration journal](journals/sqlalchemy-core-adapter-migration.md).

* **PostgreSQL session-enforcement checkpoint**: Verified live read-only session enforcement and server statement timeout behavior through the SQLAlchemy Core adapter. See the [migration journal](journals/sqlalchemy-core-adapter-migration.md).

* **Required Typst rendering checkpoint**: Verified the installed Typst compiler end-to-end and corrected report table syntax found by the real render. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Required tooling contract alignment**: Updated the specification, operations guidance, and CI to enforce the agreed Typst and local PostgreSQL tooling prerequisites. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **CI secret-scanning checkpoint**: Added Gitleaks scanning alongside dependency auditing and SBOM generation. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **ClineFlow health-enforcement checkpoint**: Preflight and doctor now execute ClineFlow/OKF health checks and reject unhealthy bundles. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Hosted cross-dialect parity checkpoint**: CI now validates all deterministic SQLite-to-PostgreSQL domain parity scenarios alongside the adapter contract. See the [migration journal](journals/sqlalchemy-core-adapter-migration.md).

* **Checksum bootstrap checkpoint**: The release bootstrap now verifies portable SHA-256 checksums before tool installation, with isolated failure-path tests. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Governed pagination checkpoint**: Added validated offset pagination through service, CLI, MCP, and receipt metadata without altering caller SQL policy. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Open-source distribution preparation**: Added a comprehensive public README covering installation, operations, safety, fixtures, parity, contribution, and releases. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Open-source publication**: Published the public [GitHub repository](https://github.com/hassanvfx/mcp-data-analysis-agent) with `main`, checkpoint tags, documentation, CI, and release workflows. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Single-source onboarding checkpoint**: Simplified public setup to one `data` source and one `MCP_DATA_SOURCE_URL` private value while retaining advanced multi-source compatibility. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).

* **Automatic multi-agent MCP setup checkpoint**: Added previewable, merge-safe configuration for all supported clients with project preference and explicit confirmation. See the [delivery goal](journals/mcp-data-analysis-agent-goal.md).
* **Simplified project bootstrap checkpoint**: Added one-confirmation `init`, a generated ignored retail playground, one private source URL, and URL-inferred SQLite/PostgreSQL dialect handling. See the [bootstrap journal](journals/simplified-project-bootstrap.md).
* **Local PostgreSQL seed and test checkpoint**: Added data-preserving local recovery/bootstrap support, reserved per-domain PostgreSQL seed schemas, and live SQLite/PostgreSQL evidence. See the [bootstrap journal](journals/simplified-project-bootstrap.md).
* **Project MCP activation checkpoint**: Activated the committed single-source policy and project client MCP definitions without tracking the generated source or private URL. See the [bootstrap journal](journals/simplified-project-bootstrap.md).
* **Shared first-run playground checkpoint**: Every supported MCP client now receives an automatically generated SQLite playground and welcome guidance before the operator switches the one private URL. See the [bootstrap journal](journals/simplified-project-bootstrap.md).
* **Current-folder repository installer checkpoint**: The documented GitHub installer now bootstraps the caller's project and detected MCP clients; bare user-level tool installation remains an explicit separate workflow. See the [bootstrap journal](journals/simplified-project-bootstrap.md).

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

* **New-user journey completion audit**: Hardened global setup application, structured MCP preflight failures, exact Continue cleanup, and the all-client hermetic demo-to-cleanup journey. See [Journey hardening implementation](journals/journey-hardening-implementation.md).

* **Operational README replacement**: Replaced legacy bootstrap-oriented public guidance with the current credential-free install, project source, analysis, and cleanup lifecycle. See [Operational README replacement](journals/operational-readme.md).

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
