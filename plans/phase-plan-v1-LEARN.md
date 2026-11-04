---
phase_loop_plan_version: 1
phase: LEARN
roadmap: specs/phase-plans-v1.md
roadmap_sha256: 06fc6fc0c3f4e6e2bda5e45f6e82130f5780db1a5dd052e1377126d21ea859f0
---
# LEARN: Local learning and maintenance

## Context
Implement the amended LEARN phase after HOST's verified discovery-to-harness-to-task flow. Preserve the existing ROUTE/HOST diff and historical evidence in this task-owned worktree. All lanes execute serially. No publication, scheduler installation, real credential provisioning, live model calls, holdouts, experiment execution, learned navigation changes or policy promotion.

HOST reports bind opaque project/workspace/producer/objective/discovery/task/decision/run identities. Successful discovery results supply guidance to harness planning; each task has its own selected/applied configuration. LEARN must preserve that distinction and derive evidence only from observed executions. Deterministic analysis is the default; operational minimum batches and intervals do not establish statistical sufficiency. Q-12/Q-13 thresholds remain unresolved and cannot be fabricated.

Selective public recovery may use `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux` as a read-only reference. Recover bounded LEARN functions/tests after inspecting them, never whole mixed application/storage/contracts modules or EXPERIMENT policy classes. Keep that worktree untouched. Use public/synthetic source bundles and isolated databases on Linux, macmini and native Windows via PowerShell; WSL is transport only.

## Interface Freeze Gates
- [ ] IF-0-HOST-1 — pre-existing, verified by `evidence/HOST/verification.json` and `evidence/HOST/closeout.json`; historical receipts are immutable and fresh inherited controls are required after LEARN source changes.
- [ ] IF-0-LEARN-1 — strict `LearningContext`/`AnalysisRequest`/`AnalysisResult` and maintenance/recovery contracts; versioned comparable evidence, bounded resumable retention and deletion-safe encrypted recovery through installed CLI/application paths.
- [ ] IF-0-VC-2 — consumed verification obligation: current-source native Linux/Darwin/Windows receipts prove every EC, and their reducer rejects omissions, stale sources, wrong commands and skipped controls.

## Lane Index & Dependencies
- SL-0 — Contracts and shared tooling; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 — Comparable analysis and durable lineage; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 — Maintenance and encrypted recovery; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 — Application, native evidence and documentation reducer; Depends on: SL-0, SL-1, SL-2; Blocks: (none); Parallel-safe: no

## Lanes

### SL-0 — Contracts and shared tooling
- **Scope**: Freeze additive learning, maintenance and recovery boundaries without weakening existing ROUTE/HOST contracts.
- **Owned files**: `baml_src/contracts.baml`, `baml_src/boundary.json`, `schemas/**`, `src/baml_sdk/**`, `src/jevdrill/contracts.py`, `docs/vocabulary.yaml`, `docs/vocabulary.md`, `pyproject.toml`, `uv.lock`, `scripts/contract_consumer.mjs`, `tests/contracts/fixtures/learn.json`, `tests/contracts/test_learn_contracts.py`
- **Interfaces provided**: `LearningContext`, `AnalysisRequest`, `EvidenceMetric`, `EvidenceGroup`, `ObjectiveAssessment`, `AnalysisResult`, `MaintenanceRequest`, `MaintenanceResult`, `RecoveryRequest`, `RecoveryResult`, `RecoveryArtifact`, `RecoveryDecision`, `RecoveryEvent`, `RecoveryBundle` and strict boundary validation.
- **Interfaces consumed**: pre-existing `CommandScope`, `DiscoveryRef`, `DiscoveryResult`, `Measurement`, `OptimizationObjective`, `ExecutionRun`, `ExecutionEvent`, `ReplayBundle`, `LocalNotice`, `Settings`.
- **Parallel-safe**: no
- **Tasks**:
  - test: Shared Python/Node fixtures reject coercion, unknown fields, invalid limits and forged lineage. Preserve v1 routing compatibility and strict discovery-v2 boundaries.
  - impl: BAML owns additive schemas; YAML owns canonical vocabulary. Learning context records task family/group, environment/isolation/evaluator/rubric revisions and explicit local/user-wide consent, plus validated discovery metadata where present. Group/results retain source measurement definitions and versioned objective assessments. Recovery carries metadata-only discovery/task linkage and deletion records sufficient to prevent resurrection; export never includes key-store credentials.
  - impl: Reuse inspected authenticated-encryption and OS-keyring dependency choices from the preserved public LEARN implementation with a regenerated lockfile. No plaintext fallback or dependency/toolchain pin changes unrelated to LEARN.
  - verify: Pinned BAML 0.20.1 generation, generated-output comparison, Python/Node fixture parity, vocabulary/import boundary checks and contract tests.

### SL-1 — Comparable analysis and durable lineage
- **Scope**: Store validated learning context and derive immutable, scoped observational revisions from actual execution reports.
- **Owned files**: `src/jevdrill/analysis.py`, `src/jevdrill/storage.py`, `src/jevdrill/evaluation.py`, `tests/analysis/**`, `tests/storage/test_learning.py`, `tests/storage/test_learning_lineage.py`, `tests/storage/test_recovery.py`, `tests/privacy/test_learning.py`
- **Interfaces provided**: `aggregate_observations`, `assess_objectives`, `record_learning_context`, `learning_observations`, `save_evidence`, `latest_evidence`, `analysis_started`, `restrict_learning` and persistence methods consumed by maintenance/recovery.
- **Interfaces consumed**: SL-0 contracts, existing durable report correction/projection, discovery reference validation, cross-producer objective tombstones, independent task tombstones and artifact staging.
- **Parallel-safe**: no
- **Tasks**:
  - test: Enter production storage/analysis for linked discovery outcomes, distinct tasks from one skill, substitutions, missing/failed/canceled runs, retain/decline preferences, superseded reports, incompatible revisions and objective reassessment.
  - impl: One owner performs additive restart-safe storage migrations; never overwrite ROUTE/HOST storage wholesale. Validate context task/decision/discovery against recorded identities. Derive selected/applied plans and status from durable reports, not untrusted caller claims. Corrected events replace effective observations without destroying source history.
  - impl: Comparable keys retain task family/group, environment/isolation, model/provider/effort/guidance and metric/evaluator/rubric revisions. Keep objective definitions/version history alongside reclassification; measured checks, preference and unknown values remain separate. No invented counterfactuals, absent units, zero-valued unknowns, whole-skill conclusions or cross-domain extrapolation.
  - impl: Minimum batch and periodic triggers update observational evidence under existing policy only. Return narrowly scoped evidence usable as explicit future discovery/task context; no automatic navigation mutation or promotion. Project/workspace is the default sharing boundary; user-wide summaries require consent on both producer context and requesting analysis, remove source/raw content, and honor opt-outs/exclusions.
  - impl: Task/objective deletion and opt-out invalidate affected derived revisions and mark validation stale without automatic rollback. Cross-producer objective tombstones suppress linked analysis even when separately scoped task reports remain. Recheck the source-observation digest before committing evidence to prevent deletion/correction races.
  - verify: Targeted analysis, storage, privacy and inherited report/discovery-deletion controls.

### SL-2 — Maintenance and encrypted recovery
- **Scope**: Implement bounded maintenance, retention notices and authenticated portable recovery that applies deletion before importing evidence.
- **Owned files**: `src/jevdrill/maintenance.py`, `src/jevdrill/integrations/archive.py`, `tests/retention/**`, `tests/maintenance/**`
- **Interfaces provided**: `Maintenance.run`, `Maintenance.schedule`, `Maintenance.restore`, `Maintenance.recover`, `archive_key`, `encrypt_archive`, `decrypt_archive`, `encode_archive`, `maintenance_lock`.
- **Interfaces consumed**: SL-0 maintenance/recovery contracts and SL-1 persistence, lineage, deletion, artifact staging and analysis invalidation.
- **Parallel-safe**: no
- **Tasks**:
  - test: Native clock-controlled fixtures prove 30-day active retention, seven-day archive grace, authenticated encrypted archival, one-year expiry and advance notices. Missing/locked/failed keys retain pending content, including headless Linux; corruption, clock rollback and crash/retry cannot silently destroy active content.
  - impl: Keep redacted measurements until deletion. Confirm archive integrity before active removal; archive expiry is measured from successful archival. Resolve only explicitly supported OS key-store backends with bounded access and no credential printing or automatic provisioning.
  - impl: Enforce process-owned non-overlap locks, bounded batches and resumable cursors. Pause/cancel and interactive contention must be observable at production scheduling/run boundaries. Deterministic analysis remains default; disabled model-assisted capability or missing budgets cannot launch model work.
  - impl: Generate inspectable systemd/launchd/Task Scheduler configurations without installing or enabling them. Correct argv quoting, explicit request paths and host contention integration must be tested on the native platform; generating configuration alone is not scheduler/run acceptance.
  - impl: Recovery/export/backup uses an explicit portable synthetic key in tests, verifies integrity and preserves metadata lineage. Apply imported and local deletion/opt-out records before restoring/importing reports, contexts, discovery bindings or analysis; malformed/conflicting bundles reject transactionally. Restoring must not remove permanent tombstones or refresh expired policy validation.
  - verify: Native lock, scheduler, pause/cancel, key failure, tamper, restore/import/export and deletion-propagation controls.

### SL-3 — Application, native evidence and documentation reducer
- **Scope**: Wire installed product commands and reduce content-bound native acceptance into reviewable LEARN readiness.
- **Owned files**: `src/jevdrill/application.py`, `src/jevdrill/cli.py`, `tests/application/test_learning.py`, `tests/cli/test_learning.py`, `tests/verification/test_learn_phase.py`, `scripts/verify_learn_phase.py`, `.github/workflows/learn.yml`, `docs/learn-interfaces.md`, `docs/learn-readiness.md`, `README.md`, `evidence/LEARN/**`
- **Interfaces provided**: installed `analyze`, `maintenance`, `recovery`, persistent scoped notices and native LEARN verification.
- **Interfaces consumed**: all SL-0 contracts, SL-1 observational persistence and all SL-2 lifecycle operations; current inherited ROUTE/HOST entrypoint/constructor controls and the separately installed HOST companion.
- **Parallel-safe**: no
- **Tasks**:
  - test: Real installed CLI and application construction sites prove linked discovery → harness decomposition → per-task execution → observations → analysis. At least two differently constrained tasks share one discovery while retaining independent outcomes/configuration; reject forged/missing linkage, deleted objectives and unsupported aggregate claims.
  - impl: Commands enforce settings/consent/exclusions and return typed results and persistent notices. Replay remains immutable; analysis or maintenance cannot recursively route or expand host permissions.
  - impl: Native collector records actual commands, assertion identities/outcomes, Python/BAML/package/schema/source digests and independent lineage/lifecycle observations. Reuse current production collector code without duplicating expensive suites. Require explicit companion configuration; preserve historical ROUTE/HOST receipts and record inherited current-source controls under LEARN.
  - test: Reducer rejects missing/duplicate platforms, stale/change-during-run sources, digest mismatches, wrong command or assertion origin, skipped/failed controls, malformed/missing records, unlinked route-v1-only evidence and fixed-count/boolean substitutes. Every EC has positive and path-entered negative controls; recomputed hashes alone cannot repair omitted controls.
  - impl: Coverage/spec-delta/readiness/docs consume every upstream lane. Record operational encryption/scheduler setup and unavailable metrics honestly; synthetic conformance supplies no empirical quality floor, causal benefit or promotion authority.
  - verify: Narrow tests first; then whole-suite inherited regressions, pinned generation, Python/Node parity, Ruff, formatting, mypy, packaging and three native installed collections followed by strict reduction. Run ignored-output and owned-file closeout audits and working/index diff checks.

## Verification
`automation.suite_command: uv run python scripts/verify_learn_phase.py --reduce-only --agent-harness /mnt/workspace/worktrees/viperjuice/agent-harness-jevdrill-discovery-host`

Native collection: `uv run python scripts/verify_learn_phase.py --local-only --agent-harness PATH`, with independent Linux/Darwin/Windows Python 3.13 receipts. The companion remains an external separately installed environment; its inspected runtime is 0.7.20/bridge 0.222.0, and native capture limitations remain explicit. JEV compiler/bridge stay 0.20.1.

Collector inputs include all current LEARN sources, schema/fixtures, protocol/control declarations, package inputs and imported-module provenance. Collection must detect source changes and enforce the 600-second bound; flag roughly five-minute proof cost. Aggregation reports multiple failures where practical. No required skips or platform simulation may substitute for native evidence. Runner-owned sealed verification records rerun the specified reduction before loop reconciliation.

## Acceptance Criteria
- [ ] EC-LEARN-1 — proven by `tests/analysis/**` and `tests/application/test_learning.py`; falsified by corrected/incompatible/missing-observation controls entering production analysis.
- [ ] EC-LEARN-2 — proven by `tests/maintenance/**` on all three native hosts; falsified by concurrent workers, pause/cancel and interactive contention entering production maintenance/scheduler paths.
- [ ] EC-LEARN-3 — proven by `tests/retention/**` on all three native hosts; falsified by unavailable keys, authenticated corruption, clock rollback and deletion-before-recovery controls.
- [ ] EC-LEARN-4 — proven by `tests/privacy/test_learning.py` and `tests/cli/test_learning.py`; falsified by opt-out/exclusion and cross-project/user-wide-consent controls entering application/CLI.
- [ ] EC-LEARN-5 — proven by `tests/storage/test_learning_lineage.py`, `tests/analysis/**` and installed flow controls; falsified by forged/deleted discovery lineage, applied-plan substitution, objective reclassification and whole-skill/cross-domain inference controls.

## Spec Closeout Plan
- schema: `spec_delta_closeout.v1`
- decision: `no_spec_delta`
- target surfaces: `docs/learn-interfaces.md`, `docs/learn-readiness.md`
- evidence paths: `evidence/LEARN/spec-delta.json`, `evidence/LEARN/verification.json`, `evidence/LEARN/closeout.json`
- redaction posture: `metadata_only`
- downstream handling: none

## Execution Notes
Implement serially in `/mnt/workspace/worktrees/viperjuice/jevdrill-route-discovery`; this assigned worktree has a deliberate authorized ROUTE/HOST baseline. Capture that baseline before editing, then classify only LEARN changes as new phase work. Preserve older mixed worktrees, historical failed plans and prior receipts. Control ownership includes this LEARN plan/review sibling, the new LEARN manifest entry, resolver-owned handoff/reflection paths and canonical `.phase-loop/**` records; do not rewrite completed source-bound evidence or legacy compatibility state.

Read only public code/docs/tests and metadata-only evidence/operational records. No user databases, private settings/corpora, actual recovery keys, credentials or release holdouts. Native hosts may receive isolated public/synthetic bundles. Generated BAML caches may be preserved outside review trees for audit. Publication, adoption and fleet/runtime changes remain separate actions. Once required checks pass, close out without further test expansion unless a new failure/change/concern justifies it.
