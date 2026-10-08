---
phase_loop_plan_version: 1
phase: PREPARE
roadmap: specs/phase-plans-v1.md
roadmap_sha256: ada9b501747182b7941d16ae59cd9859b8d1220b6f3f99c93176e8db49fdf97c
---
# PREPARE: Release preparation and governance readiness

> Replanning required: EC-PREPARE-4 adds installed acceptance of the complete
> discovery-to-task-to-feedback flow. This plan's original three criteria are
> insufficient for the amended gate. Updating the roadmap hash alone is
> insufficient. See `docs/drill-roadmap-map.md`.

## Context

This plan implements the existing PREPARE criteria after IF-0-EXPERIMENT-1.
The owner authorizes continued implementation and preparation. Publication,
canonical adoption, policy promotion and fleet activation retain separate authority.
No release holdout opens before accepted task-family thresholds are frozen.
Draft this plan now; execute its acceptance only after upstream gates are current.

Public contracts remain BAML-authored; generated Python and JSON schemas are
derived. Vocabulary YAML retains its authority. Accepted design inputs and the
original product draft remain preserved intake. Generated HTML provides a view;
it cannot replace BAML/YAML authority or mutable runtime records.
These boundaries follow JD-006, JD-052–JD-057 and JD-081–JD-082.

## Interface Freeze Gates

- [ ] IF-0-PREPARE-1 — Current native packaging/upgrade/recovery acceptance,
  complete decision/draft coverage, frozen-threshold release evaluation,
  governance dry-run representation and required independent review evidence
  agree with one prepared release input manifest. Missing or stale evidence
  prevents readiness; this gate dispatches no release.

Consumed gates: IF-0-CONTRACT-1, IF-0-ROUTE-1, IF-0-HOST-1,
IF-0-LEARN-1 and IF-0-EXPERIMENT-1. Preserve existing EC text and platform matrix.

Internal release-input artifact fields: source digest, package version, wheel and
sdist digests, lock/schema/vocabulary digests, companion identity, native report
references, calibration/evaluator revisions, release evaluation reference,
coverage/dry-run/review references, installation and rollback references,
publication_performed=false and canonical_adoption=false. All references carry
repo-relative paths and SHA-256 citations. No secrets, private paths or raw
provider responses enter the public manifest. No new product contract is introduced.

## Lane Index & Dependencies

- SL-0 — Packaging and platform readiness; Depends on: (none, all upstream gates);
  Blocks: SL-1; Parallel-safe: no.
- SL-1 — Documentation, governance and final evidence; Depends on: SL-0;
  Blocks: (none); Parallel-safe: no.

Execute these two lanes serially in the assigned worktree. Do not dispatch agents.

## Lanes

### SL-0 — Packaging and platform readiness

- **Scope**: Prepare matching release metadata and verify native installed-package,
  upgrade, migration, recovery and rollback behavior.
- **Owned files**: `pyproject.toml`, `uv.lock`, `CHANGELOG.md`,
  `.github/workflows/release.yml`, `scripts/verify_prepare_platform.py`,
  `tests/release/test_package_upgrade.py`, `tests/release/test_recovery.py`,
  `tests/release/test_release_inputs.py`, `evidence/PREPARE/platforms/**`,
  `evidence/PREPARE/package.json`, `evidence/PREPARE/release-inputs.json`.
- **Interfaces provided**: Native collection command
  `python scripts/verify_prepare_platform.py --local-only`, package/lock/source
  bindings and the prepared release inputs artifact.
- **Interfaces consumed**: Existing strict schemas, storage migrations,
  recovery commands, installed-CLI acceptance and companion fingerprints;
  accepted frozen calibration and separately sealed release protocol.
- **Parallel-safe**: no.
- **Tasks**:
  - test: Real package installation outside the checkout; baseline upgrade and
    replay; interrupted migration/recovery; retained deletion tombstones;
    rollback without incompatible storage downgrade; mismatched package/schema/
    source/companion evidence must fail.
  - impl: Use the existing V0 locked isolated-install and replay patterns without
    resetting its grants or replacing historical evidence. Prepare
    `0.1.0rc1` package metadata/changelog consistently; regenerate only the lock
    changes required by that version. No package publishing workflow runs.
    Keep development V0 artifacts available for documented rollback.
  - impl: Implement native collection with runner identity, OS/runtime, exact
    commands, input/output hashes, assertions and elapsed time. Require Linux,
    native macOS and native Windows; WSL does not replace Windows. Flag proofs
    beyond roughly five minutes and retain all failures.
  - impl: Configure the prepared workflow for explicit future dispatch only;
    immutable artifact/version inputs and separate publication authority are
    required. Do not include embedded credentials or activate it during this phase.
  - verify: `uv sync --locked`;
    `uv run pytest -q tests/release/test_package_upgrade.py tests/release/test_recovery.py tests/release/test_release_inputs.py`;
    native `uv run python scripts/verify_prepare_platform.py --local-only`.

### SL-1 — Documentation, governance and final evidence

- **Scope**: Reconcile all requirements, prove governance representation in an
  isolated dry run, and reduce current acceptance into a reviewable release handoff.
- **Owned files**: `README.md`, `docs/release-readiness.md`,
  `docs/release-runbook.md`, `docs/roadmap-status.md`,
  `scripts/verify_prepare_phase.py`, `scripts/verify_adoption_dry_run.py`,
  `tests/release/test_prepare_phase.py`, `tests/release/test_adoption_dry_run.py`,
  `evidence/decision-coverage.json`, `evidence/PREPARE/coverage.json`,
  `evidence/PREPARE/spec-delta.json`, `evidence/PREPARE/adoption-dry-run.json`,
  `evidence/PREPARE/adoption-inputs/**`, `evidence/PREPARE/release-evaluation.json`,
  `evidence/PREPARE/review/**`, `evidence/PREPARE/verification.json`.
- **Interfaces provided**: `python scripts/verify_prepare_phase.py --reduce-only`;
  complete EC/decision/draft coverage, metadata-only dry-run, review and runbook.
- **Interfaces consumed**: All SL-0 outputs, all upstream native/operational gates,
  accepted calibration and release protocol, reviewed governed-pipeline source-role
  and task-representation contracts, actual cross-vendor review evidence.
- **Parallel-safe**: no.
- **Tasks**:
  - test: The reducer rejects missing platforms, skipped assertions, stale source
    bindings, unchecked decisions/draft requirements, premature holdout exposure,
    unmet floors, inadequate samples and missing required review evidence.
  - impl: Map every stable JD decision and unchanged numbered product-draft
    requirement to exact evidence or an explicit deferred scope. A deferment that
    changes public scope requires an owner decision; do not silently weaken ECs.
  - impl: Prepare adoption inputs and run only the existing governed-pipeline
    source-role/representation validators in owned disposable fixtures. Compare
    aliases, unchanged EC IDs, gates and dependency edges with the Harness parsed
    roadmap. Exercise swapped authority and missing-edge negative controls.
    Generated HTML remains a projection. No writes to this repo's `.pipeline/**`,
    sibling repos, canonical registries, archives or managed mirrors are authorized.
    Any later actual intake or synthesis requires its own reviewed adoption action.
  - impl: Read frozen thresholds and exposure registry before release evaluation.
    Refuse access when they are absent, changed, already exposed or insufficient.
    Any new model execution needs a separately recorded allowance. Preserve raw
    measurements in their permitted private store and publish metadata only.
  - impl: Obtain required cross-vendor plan/implementation review with the board
    president reconciliation. Give manually launched adapters short file pointers
    and tool access. Preserve disagreement and limitations. Offline lint or one
    model's opinion cannot be reported as ratified review.
  - impl: Document exact installation, migration, recovery, unsupported execution,
    rollback and separate release/adoption authorization. Write spec-delta
    `governed_pipeline_refresh` as metadata-only deferral with
    `publication_performed=false`, `canonical_adoption=false`.
  - verify: `uv run pytest -q tests/release/test_prepare_phase.py tests/release/test_adoption_dry_run.py`;
    `uv run python scripts/verify_adoption_dry_run.py`;
    `uv run python scripts/verify_prepare_phase.py --reduce-only`.

## Verification

Preflight locked Python dependencies, Node dependencies, the pinned BAML 0.20.1
compiler and assigned companion. New commands above are implementation deliverables.
Run targeted release controls before full acceptance:
`uv run pytest -q`, generation/schema/vocabulary/import/lint/format/type checks,
original phase reducers and native PREPARE collection/reduction.
Record all command results and proof-cost findings. Keep earlier failures immutable.

automation.suite_command: uv run python scripts/verify_prepare_phase.py --reduce-only

## Acceptance Criteria

- [ ] EC-PREPARE-1 — proven by native
  `scripts/verify_prepare_platform.py --local-only` plus the original upstream
  reducers and frozen-threshold release evaluation; falsified by source/package
  mismatch, interrupted upgrade, bad recovery, unmet floors or insufficient samples.
- [ ] EC-PREPARE-2 — proven by
  `scripts/verify_adoption_dry_run.py`, decision/draft coverage and the final
  reducer; falsified by missing requirements, changed EC/gate/alias/dependency,
  reversed YAML/BAML authority or attempted canonical writes.
- [ ] EC-PREPARE-3 — proven by
  `scripts/verify_prepare_phase.py --reduce-only`, actual required cross-vendor
  review/reconciliation and the release/rollback handoff; falsified by missing
  review evidence, unbound release inputs or any publication/adoption claim.

## Execution readiness

Planning may complete while EXPERIMENT remains blocked. Phase acceptance waits for
current upstream native/operational evidence, empirical frozen thresholds and any
separate live allowance. The sealed release dataset remains unopened.
Release dispatch is a later separately authorized action; this plan does not use
`phase_loop_mutation: release_dispatch`.
