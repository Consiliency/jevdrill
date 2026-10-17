---
phase_loop_plan_version: 1
phase: EXPERIMENT
roadmap: specs/phase-plans-v1.md
roadmap_sha256: 06fc6fc0c3f4e6e2bda5e45f6e82130f5780db1a5dd052e1377126d21ea859f0
---
# EXPERIMENT: Comparisons and governed policy updates

## Context
Continue after current-source LEARN acceptance in the assigned task worktree. Implement the amended roadmap without weakening its four criteria. Execute all lanes serially, with one fresh implementation worker and no delegated writer fanout. Preserve ROUTE/HOST/LEARN source protections, existing work and immutable historical receipts.

Prior paid-pilot grants and conservative reservations are unchanged; prior Gemma authority covers only its already exposed twelve-case study. No new provider/model calls, budget replenishment, credentials, private tasks, policy/release holdouts, policy activation, scheduler installation, fleet adoption or publication are authorized here. Public synthetic local HTTP responses and actual already installed restricted Linux containers may verify adapter behavior. These prove software boundaries, not empirical model quality.

Complete every independent offline implementation and native proof before requesting a real owner decision. Prepare a concrete representative development protocol and bounded resource/cost proposal for owner review as required by `docs/roadmap-status.md`. Q-12/Q-13 empirical floors and tolerances remain pending; retain the accepted rule of no additional critical failures. Do not invent calibrated values, treat fixtures as empirical evidence, or mark the whole phase complete while an unchanged criterion lacks proof.

Read-only recovery source: `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux`. Inspect and selectively recover bounded EXPERIMENT functions/tests; never copy its mixed storage, application, contracts, analysis or routing modules wholesale. Companion source is read-only unless an exact separate companion-owned plan is recorded first. Production gaps repairable in code are non-human work, not grounds for stopping at an owner decision.

## Interface Freeze Gates
- [ ] IF-0-LEARN-1 — consumed current-source LEARN contracts, durable source lineage, scoped invalidation, retention/recovery and installed discovery-to-analysis proof; historical receipts remain immutable.
- [ ] IF-0-EXPERIMENT-1 — strict experiment proposal/admission/execution and policy definition/calibration/evaluation/lifecycle boundaries; durable transitions, scoped reservations, trusted runner/evaluator ports and bounded candidate-ordering changes.
- [ ] IF-0-VC-2 — consumed current-source native Linux/Darwin/Windows and operational proof obligation; no proxy or empirical fixture waiver.

## Lane Index & Dependencies
- SL-0 — Contracts and shared tooling; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 — Admission and bounded execution; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 — Independent evaluation and policy lifecycle; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 — Installed evidence and development protocol reducer; Depends on: SL-0, SL-1, SL-2; Blocks: (none); Parallel-safe: no

## Lanes

### SL-0 — Contracts and shared tooling
- **Scope**: Freeze additive strict EXPERIMENT contracts and generated tooling while preserving all inherited boundaries.
- **Owned files**: `baml_src/contracts.baml`, `baml_src/boundary.json`, `baml_src/development.baml`, `schemas/**`, `src/baml_sdk/**`, `src/jevdrill/contracts.py`, `scripts/check_generated_contracts.py`, `scripts/contract_consumer.mjs`, `docs/vocabulary.yaml`, `docs/vocabulary.md`, `pyproject.toml`, `uv.lock`, `tests/contracts/fixtures/experiment.json`, `tests/contracts/test_experiment_contracts.py`
- **Interfaces provided**: strict experiment request/result/proposal/authorization/readiness/execution records; policy definition/calibration/evaluation/authorization/lifecycle records; bounded development BAML request/response functions.
- **Interfaces consumed**: pre-existing comparison limits, optimization objectives, command scope, execution plans/events, discovery references, learning observation source metadata and measurement semantics.
- **Parallel-safe**: no
- **Tasks**:
  - test: Shared Python/Node fixtures reject undeclared fields, coercion, invalid bounds, scope mismatches, missing calibration/provenance and forged readiness. Preserve v1 compatibility and discovery-v2 strictness.
  - impl: BAML owns public types and boundary metadata owns semantic constraints; YAML owns vocabulary. Generate additive artifacts using pinned compiler/bridge 0.20.1. Register experiment/promotion test paths. Recover only bounded development BAML functions needed for local HTTP verification, with no automatic credential access or retries.
  - verify: Generation comparison, contract/import/vocabulary checks and shared Python/Node parity before service implementation.

### SL-1 — Admission and bounded execution
- **Scope**: Persist recurring proposals and execute only explicitly enabled comparisons under verified scope, resource, cost and recovery bounds.
- **Owned files**: `src/jevdrill/experiments.py`, `src/jevdrill/storage.py`, `src/jevdrill/integrations/experiments.py`, `src/jevdrill/integrations/development.py`, `src/jevdrill/integrations/archive.py`, `tests/experiments/**`, `tests/storage/test_experiments.py`
- **Interfaces provided**: `Experiments`, `ExperimentRunner`, `RestrictedContainerRunner`, `DevelopmentRunner`, `IndependentDevelopmentGrader` and durable experiment/policy persistence.
- **Interfaces consumed**: SL-0 contracts; existing report/lineage/tombstone/recovery storage and native custody locks; all persisted interfaces required by SL-2.
- **Parallel-safe**: no
- **Tasks**:
  - test: Enter production admission for duplicate proposals, priority/recurrence, disabled settings, absent/expired/revoked authority, missing limits, concurrent reservations, daily rollover, uncertain acknowledgments, deleted context and external side effects.
  - impl: One owner performs additive restart-safe migrations, including SL-2 policy storage. Bind proposals to authoritative task/discovery/context and immutable candidate fingerprints. Version deterministic priority without invented expected outcomes. Counts default to one background comparison/two candidates and confer no authority. Reserve verified upper raw costs transactionally before dispatch; deletion, cancellation, restart or small observed bills cannot refund uncertain reservations.
  - impl: Implement immediate host acceptance and deferred/internal trusted runner ports, explicit prepare/start/poll/cancel transitions, durable pre-start cancellation and no automatic redispatch after uncertainty. Check final context, isolation, capabilities, deadlines, interactive contention and resource/cost enforcement independently of caller claims. Unavailable/unbounded adapters return honest non-ready/partial states.
  - impl: Internal generated code uses only the inspected already installed immutable Linux image, copied synthetic inputs, no host credentials/sockets/network, least privilege, enforced CPU/memory/process/output limits and a container-owned absolute deadline. Verify complete descendant cleanup and custody after worker death; no image pulls. Native unsupported internal runtimes disable execution. Preserve observed host isolation and never duplicate external side effects in shadow comparisons.
  - impl: Bounded explicitly pumped development worker preserves request/usage/output provenance and separates host preference from checks. Local HTTP fixtures may invoke the real BAML transport; no remote model endpoint or live spending. Keep prior study ledgers and profiles untouched.
  - verify: Targeted experiment/storage tests, actual Linux restricted-container proofs, native cancellation/contending-process/restart controls and unavailable-runtime denials.

### SL-2 — Independent evaluation and policy lifecycle
- **Scope**: Evaluate recorded comparisons under predeclared calibration and govern separately authorized, scope-bounded candidate ordering.
- **Owned files**: `src/jevdrill/evaluation.py`, `src/jevdrill/analysis.py`, `src/jevdrill/routing.py`, `tests/promotion/**`, `tests/evaluation/test_policy_evaluation.py`, `tests/evaluation/test_review_scoring.py`, `tests/routing/test_routing.py`
- **Interfaces provided**: `evaluate_policy`, `RecordedPolicyEvidence`, `PolicyLifecycle` and bounded routing candidate ordering.
- **Interfaces consumed**: SL-0 policy/calibration contracts; SL-1 immutable proposal/receipt/observation/exposure storage and independent grader; inherited scoped LEARN invalidation and authoritative discovery lineage.
- **Parallel-safe**: no
- **Tasks**:
  - test: Production evaluation rejects missing/late calibration, fabricated/unblinded evaluator provenance, wrong membership or related-group splits, exposed/release holdouts, missing outcomes, critical regressions despite average gains, insufficient samples and changed supporting data.
  - impl: Freeze trusted study membership, baseline/candidate plans, evaluator/rubric revisions and external exposure history before admission/evaluation. Durable exposure precedes independent grading; grading receives anonymous output artifacts and records its revision. Preserve measurements and objective reclassification separately from preferences; never use candidate self-reports as independent integrity checks.
  - impl: Only separate promotion authority can enable bounded rollout for approved task groups. Change candidate ordering only; eligibility, permissions, caller constraints, required guidance and budgets retain precedence. Enforce pinned revisions and transactional route caps. Deletion/opt-out makes only affected validation stale; regression suspends the affected version/scopes, returning a currently verified fallback or explicit non-ready.
  - verify: Targeted lifecycle/recorded-evidence/routing controls, local actual restricted-grader connection with correct and critical-failure outputs, denied promotion, exposure/restart races and inherited unrelated-history/deletion controls. Synthetic calibration values establish software behavior only.

### SL-3 — Installed evidence and development protocol reducer
- **Scope**: Wire installed application/CLI, collect current-source native proofs, and prepare the remaining study for owner review.
- **Owned files**: `src/jevdrill/application.py`, `src/jevdrill/cli.py`, `tests/application/test_experiments.py`, `tests/cli/test_experiments.py`, `tests/verification/test_experiment_phase.py`, `tests/verification/test_development_runtime.py`, `tests/verification/test_calibration_benchmark.py`, `tests/verification/test_discovery_calibration.py`, `scripts/verify_experiment_phase.py`, `scripts/verify_route_phase.py`, `scripts/verify_development_runtime.py`, `scripts/verify_calibration_benchmark.py`, `scripts/verify_discovery_calibration.py`, `research/evaluation/discovery-calibration/**`, `.github/workflows/experiment.yml`, `docs/experiment-interfaces.md`, `docs/experiment-readiness.md`, `docs/evaluation-protocol.md`, `docs/contract-decisions.md`, `docs/roadmap-status.md`, `README.md`, `evidence/EXPERIMENT/**`
- **Interfaces provided**: installed experiment/admission/execution/policy commands; native/software/operational/study evidence reduction; reviewable development protocol and bounded allowance proposal.
- **Interfaces consumed**: every SL-0/SL-1/SL-2 finding, inherited current-source ROUTE/HOST/LEARN controls and separately installed HOST companion.
- **Parallel-safe**: no
- **Tasks**:
  - test: Real installed commands and production construction prove linkage, settings/authority denials, host/deferred recovery, cancellation, proposal/policy deletion and bounded candidate ordering. Distinct tasks from one discovered skill retain their task-specific configuration.
  - impl: Explicit adapter configuration and typed readiness keep missing host/runtime/evaluator capabilities visible. Reuse inherited current-source collection without duplicating expensive suites; preserve historical receipts. Observe actual Python/package/compiler versions, imported module/source hashes, exact commands and assertion identities on Linux/Darwin/native Windows. WSL is transport only.
  - impl: Bounded ownership amendment: preserve only the inherited `scripts/verify_route_phase.py` public verification TemporaryDirectory generation outside the review tree using `delete=False`. Keep ordinary native Windows paths, every original suite/assertion, immutable historical receipts and independently verified production cleanup. No other inherited collector behavior or Windows security settings may change.
  - test: Strict reducer rejects missing/duplicate/stale platforms, wrong commands/origins, omitted companion extras, failed/skipped controls, fabricated capabilities/calibration/study outcomes, and phase-complete claims based solely on software checks. Each EC has positive and path-entered negative controls; EC-4 requires genuine preregistered linked decisions/outcomes, not executor bug scores.
  - impl: Prepare an explicitly exposed, purpose-built representative development corpus for implementation/review/documentation. Include ambiguous/cross-domain discovery, no useful optional guidance, changed objectives and one skill with differing task needs. Independently predeclare acceptable selections, unsuitable controls, outcome checks, related groups, revisions and analysis before execution. Compare actual discovery/task routing with applicable fixed-default, cheapest-feasible, no-guidance, previous-policy and simple-retrieval baselines; explain any inapplicability. Offline reference/defect/always-admit/all-default tests validate the evaluator without becoming empirical results.
  - impl: Write a concrete study protocol/preview that specifies candidate revisions, capped attempts/concurrency/output/time/compute/cost, durable reservations, exposure logging, pause/cancel, no retries, stopping rules and uncertainty/unknown telemetry. Distinguish calibration from fresh policy evaluation and untouched release holdout; propose task-family tolerance calibration under no additional critical failures. New study execution remains disabled until an explicit new allowance; identify exact remaining owner inputs and preserve prior reservations.
  - verify: Narrow tests, whole-suite regressions, pinned generation/Python-Node parity/Ruff/format/mypy/package checks, three native installed collections and actual Linux operational probes. Run ignored-output/owned-file/diff audits. Seal the original reducer through runtime verification; record software proof separately from incomplete empirical/operational gates and never produce IF-0-EXPERIMENT-1 until all four unchanged ECs pass.

## Verification
`automation.suite_command: uv run python scripts/verify_experiment_phase.py --reduce-only --agent-harness /mnt/workspace/worktrees/viperjuice/agent-harness-jevdrill-discovery-host`

Native collection: `uv run python scripts/verify_experiment_phase.py --local-only --agent-harness PATH`. The reducer may provide a clearly labeled `--software-only` diagnostic; this cannot satisfy the phase suite or unblock PREPARE. Operational Linux probes use `scripts/verify_development_runtime.py --image-id INSPECTED_ID`; offline corpus verification uses `scripts/verify_discovery_calibration.py --offline-only`. No live study is dispatched.

Require current input digests across every receipt, explicit inherited controls/companion platform extras and independent installed source provenance. Preserve every failed/previous receipt. Bound each native collection to 600 seconds and flag roughly five-minute proof cost. Missing operational/empirical proof stays explicit; repair local gaps before escalating. Close out after required authorized checks pass without extra expansion absent new failures/changes/concerns.

## Acceptance Criteria
- [ ] EC-EXPERIMENT-1 — proven by `tests/experiments/**` and `tests/storage/test_experiments.py`; falsified by disabled authority, missing limits and concurrent-budget controls entering production admission.
- [ ] EC-EXPERIMENT-2 — proven by native installed execution/recovery and `scripts/verify_development_runtime.py`; falsified by deadline, pause/cancel, missing context, unsupported isolation, contention, worker-death and side-effect controls.
- [ ] EC-EXPERIMENT-3 — proven by persistent lifecycle and recorded independent evaluation; falsified by critical regression, unblinded/exposed holdout, stale/deleted support and unauthorized promotion controls. Empirically uncalibrated values remain unverified.
- [ ] EC-EXPERIMENT-4 — proven by the preregistered development study receipt and `scripts/verify_discovery_calibration.py`; falsified by entered always-admit/all-default/unsuitable controls, provenance/overhead omissions and executor-score-only substitutes. An offline corpus/protocol alone cannot close this criterion.

## Spec Closeout Plan
- schema: `spec_delta_closeout.v1`
- decision: `no_spec_delta`
- target surfaces: `docs/experiment-interfaces.md`, `docs/experiment-readiness.md`, `docs/evaluation-protocol.md`
- evidence paths: `evidence/EXPERIMENT/spec-delta.json`, `evidence/EXPERIMENT/verification.json`, `evidence/EXPERIMENT/closeout.json`, `evidence/EXPERIMENT/study-proposal.json`
- redaction posture: `metadata_only`
- downstream handling: none

## Execution Notes
Assigned worktree: `/mnt/workspace/worktrees/viperjuice/jevdrill-route-discovery`, authorized dirty baseline captured before edits. All lanes are serial; persistence changes needed by SL-2 belong to SL-1. Control ownership includes this plan/review sibling, its new manifest entry, resolver-owned handoff/reflection paths and canonical `.phase-loop/**`. Do not edit completed source-bound evidence, old mixed worktrees, original main, credentials, user databases, private corpora or sealed holdouts.

Source bundles and synthetic keys/databases may reach isolated native task environments. Preserve generated caches outside review trees for audit. No commits, pushes, PRs, merges, service changes or external publication. PREPARE waits for actual EXPERIMENT acceptance; missing owner calibration/study authorization is reported only after concrete independent work and the proposal are reviewable.
