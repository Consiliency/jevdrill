---
phase_loop_plan_version: 1
phase: LEARN
roadmap: specs/phase-plans-v1.md
roadmap_sha256: a5cbd9e6d924385cc6a2e286b394b1408fa5a568176cee74b8b40524466cc86a
---
# LEARN: Local learning and maintenance

> Replanning required: EC-LEARN-5 adds discovery/task lineage and scoped feedback.
> Preserve this plan's prior evidence; revise against the amended upstream flow.
> Updating the roadmap hash alone is insufficient. See `docs/drill-roadmap-map.md`.

## Context
Continue the verified HOST implementation in its existing task-owned worktree. Preserve prior changes. Execute sequentially; no publication, scheduler installation, credential provisioning, model calls, experiments or policy promotion. Existing HOST evidence proves its recorded inputs; LEARN changes require new regression evidence.

Implement JD-028–031, JD-038–045, JD-066–072 and JD-074–076 within the roadmap's LEARN boundary. Local deterministic analysis is enabled by default. Empirical promotion thresholds remain unresolved and cannot be fabricated. Configurable analysis batch size and interval are operational triggers, not claims of statistical sufficiency.

## Interface Freeze Gates
- [ ] IF-0-LEARN-1 — BAML learning/maintenance requests, comparable evidence revisions, resumable scoped maintenance and deletion-safe encrypted recovery, proven on native Linux/macOS/Windows.

## Lane Index & Dependencies
SL-0 — Contracts
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-3
  Parallel-safe: no

SL-1 — Analysis and persistence
  Depends on: SL-0
  Blocks: SL-2, SL-3
  Parallel-safe: no

SL-2 — Maintenance and recovery
  Depends on: SL-0, SL-1
  Blocks: SL-3
  Parallel-safe: no

SL-3 — Application, verification and docs reducer
  Depends on: SL-0, SL-1, SL-2
  Blocks: (none)
  Parallel-safe: no

## Lanes
### SL-0 — Contracts
- **Scope**: Freeze strict BAML request/result contracts, configuration and dependency boundaries.
- **Owned files**: `baml_src/contracts.baml`, `baml_src/boundary.json`, `schemas/**`, `src/baml_sdk/**`, `docs/vocabulary.yaml`, `docs/vocabulary.md`, `pyproject.toml`, `uv.lock`, `tests/contracts/fixtures/learn.json`, `tests/contracts/test_learn_contracts.py`
- **Interfaces provided**: `LearningContext`, `AnalysisRequest`, `AnalysisResult`, `MaintenanceRequest`, `MaintenanceResult`, `RecoveryRequest`, `RecoveryResult`, `RecoveryBundle`
- **Interfaces consumed**: `CommandScope`, `Measurement`, `OptimizationObjective`, `Settings`, `ExecutionEvent` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Positive/negative shared fixtures reject coercion, unknown fields and invalid limits.
  - impl: Generate Python and portable schemas from BAML; register vocabulary and approved authenticated-encryption/OS-keyring dependencies.
  - verify: Generated outputs, Python/Node fixtures, vocabulary and imports.

### SL-1 — Analysis and persistence
- **Scope**: Derive versioned observational evidence from stored executions and explicitly supplied comparable context.
- **Owned files**: `src/jevdrill/analysis.py`, `src/jevdrill/storage.py`, `tests/analysis/**`, `tests/storage/test_learning.py`
- **Interfaces provided**: `aggregate_observations`, `learning_observations`, `save_evidence`, `stage_artifact`, `restrict_learning`
- **Interfaces consumed**: `LearningContext`, `AnalysisRequest`, `AnalysisResult`
- **Parallel-safe**: no
- **Tasks**:
  - test: Corrections, missing/failed/canceled observations, incompatible revisions, opt-out, project isolation, shared provenance and task deletion.
  - impl: Persist learning context linked to task/decision; aggregate only actual applied executions; preserve source metric definitions and objective history. Minimum-batch and periodic triggers update evidence without policy promotion; deletion invalidates derived evidence and marks policy validation stale.
  - verify: Targeted analysis/storage regressions.

### SL-2 — Maintenance and recovery
- **Scope**: Implement bounded local maintenance, encrypted retention, restoration and portable recovery.
- **Owned files**: `src/jevdrill/maintenance.py`, `src/jevdrill/integrations/archive.py`, `tests/retention/**`, `tests/maintenance/**`
- **Interfaces provided**: `Maintenance.run`, `Maintenance.recover`, `Maintenance.schedule`
- **Interfaces consumed**: `stage_artifact`, `MaintenanceRequest`, `RecoveryRequest`, `RecoveryBundle`
- **Parallel-safe**: no
- **Tasks**:
  - test: Crash/retry, overlap, clock rollback, 30+7-day transition, missing/failed keys, tampering, expiry notices, deletion before restore/import, portable recovery.
  - impl: Process bounded batches and exit; OS scheduler configuration is explicit and never installed silently. Encrypt with authenticated encryption, verify before active removal, keep keyless content pending, expire one year after archival with advance notice. Export uses an explicit recovery key; imports apply deletion records first and reject conflicts.
  - verify: Native scheduler/pause/cancel/retention/recovery tests.

### SL-3 — Application, verification and docs reducer
- **Scope**: Wire production CLI/application entrypoints and reduce independent native evidence.
- **Owned files**: `src/jevdrill/application.py`, `src/jevdrill/cli.py`, `tests/application/test_learning.py`, `tests/cli/test_learning.py`, `scripts/verify_learn_phase.py`, `tests/verification/test_learn_phase.py`, `docs/learn-interfaces.md`, `docs/learn-readiness.md`, `README.md`, `evidence/LEARN/**`
- **Interfaces provided**: `analyze`, `maintenance`, `recovery`, `learn_native_verification`
- **Interfaces consumed**: `aggregate_observations`, `learning_observations`, `save_evidence`, `restrict_learning`, `Maintenance.run`, `Maintenance.recover`, `AnalysisResult`, `MaintenanceResult`, `RecoveryResult`
- **Parallel-safe**: no
- **Tasks**:
  - test: Real CLI and application construction-site controls prove commands invoke production behavior; native reducer rejects missing/stale/failed/skipped platform evidence.
  - impl: Integrate settings, notices and verified analysis revisions without expanding authority. Document operational setup, pending key failures, limits and recovery.
  - verify: Whole-suite regression, packaging, type/lint checks, native matrix.

## Verification

`automation.suite_command: uv run python scripts/verify_learn_phase.py --reduce-only`

Use the existing pinned Python 3.13 environment. Refresh dependencies after manifest edits. Run narrow tests first; then `uv run pytest`, generated checks, Python/Node parity, vocabulary/import checks, Ruff, mypy and build. Native LEARN collection runs `python scripts/verify_learn_phase.py --local-only` on Linux, Darwin and Windows; `--reduce-only` verifies matching hashes and zero required skips. Runner evidence must retain commands and results. No live provider/model calls or release holdout access. Flag collection above 300 seconds.

## Acceptance Criteria
- [ ] EC-LEARN-1 — proven by `tests/analysis` and `tests/application/test_learning.py`; falsified by incompatible/corrected/unknown source controls through production analysis.
- [ ] EC-LEARN-2 — proven by `tests/maintenance` on three native platforms; falsified by concurrent maintenance, pause/cancel and interactive contention controls entering the production scheduler.
- [ ] EC-LEARN-3 — proven by `tests/retention` on three native platforms; falsified by unavailable keys, corrupted archives, clock rollback and deletion-before-import controls entering production recovery.
- [ ] EC-LEARN-4 — proven by `tests/analysis` and `tests/cli/test_learning.py`; falsified by opt-out and cross-project evidence controls entering application/CLI commands.

## Spec Closeout Plan
- schema: `spec_delta_closeout.v1`
- decision: `no_spec_delta`
- target surfaces: `docs/learn-interfaces.md`, `docs/learn-readiness.md`
- evidence paths: `evidence/LEARN/spec-delta.json`, `evidence/LEARN/verification.json`
- redaction posture: `metadata_only`
- downstream handling: none

## Execution bounds and read access
Read repository code/docs/fixtures and metadata-only prior phase evidence; generated .phase-loop runner logs and skill handoffs/reflections are authorized operational records. No user databases, local overrides, raw corpora, real recovery keys or credentials are needed. Native proof uses isolated synthetic databases and keys. Existing task worktrees on macmini and win-wsl may receive this task's source snapshots. Prior task-owned dirty files remain preserved, with ownership limited to the lanes above.

## Execution Notes

Execute the lanes sequentially in the existing task-owned worktree. The suite reduces fresh native platform collections; it cannot produce the gate from a local-only run. No external release dispatch occurs. Preserve generated `.baml/` compiler caches outside the checkout when the closeout audit cannot classify them. Q-12/Q-13 policy-promotion tolerances remain an owner decision for EXPERIMENT; observational LEARN verification does not supply them.
