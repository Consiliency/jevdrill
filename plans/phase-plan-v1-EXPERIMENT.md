---
phase_loop_plan_version: 1
phase: EXPERIMENT
roadmap: specs/phase-plans-v1.md
roadmap_sha256: ada9b501747182b7941d16ae59cd9859b8d1220b6f3f99c93176e8db49fdf97c
---
# EXPERIMENT: Comparisons and governed policy updates

> Replanning required: EC-EXPERIMENT-4 requires discovery/routing discrimination
> evidence. Preserve earlier experiment results without treating executor scores
> as proof of this criterion. Updating the roadmap hash alone is insufficient.
> See `docs/drill-roadmap-map.md`; existing spending authority is unchanged.

Owner follow-up on 2026-09-29 authorizes separate review scoring and two clarified review comparisons with the same candidates and existing cumulative pilot limits. Preserve original prompts, responses and scores. Record rescoring as a new derived artifact; freeze the revised rubric and prompts before new calls. This approval does not enable a broader study or policy promotion.

The owner also approved a separately versioned structured BAML review response path, verified with local HTTP fixtures before further paid comparisons. Preserve the original pilot BAML source and experiment digests.

The subsequent owner request, "Okay, please run the scoped live comparison," authorizes one structured comparison of the existing correct-clamp exercise using the same two model snapshots and cumulative pilot limits. Remaining retained reservations permit one pair. Freeze the new condition and rubric before dispatch, use the same durable ledger, and preserve all prior evidence. No promotion or broader study is authorized.

## Context
Owner continuation after the runtime proof authorizes repairing generated-output provenance. SL-3 additionally owns `.phase-loop-generated-outputs.json` and `scripts/verify_generated_outputs.py`; SL-0 may regenerate the existing BAML SDK. Read and preserve build artifacts under `.baml/**`, `dist/**` and `src/baml_sdk/typesafe_patch/**` to identify their actual producers. A clean reproduction may use purpose-built scratch directories under `.phase-loop/runs/EXPERIMENT-provenance-*/**`, with all displaced files retained. The declaration must name actual bounded build commands, not accept files based on directory names. Installing a committed declaration requires a separate local-commit decision; no publication is implied. Continue independent operational checks while that decision is pending.

SL-2 continues EC-EXPERIMENT-3 with an explicit Linux-only operational probe in `tests/promotion/runtime_recorded_evidence.py` (outside automatic portable test discovery). Connect the existing persistent development runner, recorded-comparison evaluator and independent restricted grader using purpose-built local HTTP responses. Freeze the actual grader revision before dispatch, test correct and critically failing candidates, require exposure before grading and verify no additional provider calls or promotion. SL-3 includes both probes in the existing runtime verifier with exact JUnit identities. These operational probes establish the adapter connection, not empirical quality thresholds or whole-phase acceptance.

Owner continuation on 2026-10-06 resumes EC-EXPERIMENT-2 with the existing Linux development runner. SL-3 extends its real-runtime verifier to require cancellation, restart, uncertain-call recovery, concurrent dispatch and worker-death checks, plus rejection of an unavailable image. It additionally owns `tests/verification/test_development_runtime.py`. Use local synthetic HTTP responses and the already installed immutable image; no paid calls, image pulls, policy activation or holdout access. Logs and historical reports are allowed under `.phase-loop/runs/EXPERIMENT-development-*/**` and `evidence/EXPERIMENT/**`. This is partial EC-EXPERIMENT-2 evidence: general host-assisted execution, the native matrix and independent recorded-policy evaluation remain required. The roadmap pin is refreshed without changing its acceptance criteria.

Owner approval on 2026-10-01, "Okay, let's do it," authorizes a bounded local Gemma development benchmark through BAML against the existing served model on `ai`. Use only the purpose-built exposed corpus, with thinking enabled and disabled as the two conditions. Freeze the protocol before dispatch: 12 cases, at most 24 generation attempts, one request at a time, no retries or output repair calls, 60 seconds and 2,048 output tokens per attempt, 120 seconds per pair. The pre-existing model service owns its GPU allocation; do not restart it, download models, change service configuration or displace interactive work. Independent generated-code grading retains the installed Linux container's 2 CPU / 2 GiB limits. Preserve attempted and uncertain calls in a durable study ledger; this is a new local resource authorization, not replenishment of the original paid ledger. External paid calls and policy promotion remain disabled. SL-1 appends a separate local BAML client to `baml_src/development.baml` without modifying the historical paid-pilot sources. SL-3 additionally owns `scripts/run_local_calibration.py` and `tests/verification/test_local_calibration.py`, with purpose-built local responses/results in `evidence/EXPERIMENT/local-gemma/**` and its durable ledger/logs in `.phase-loop/runs/EXPERIMENT-gemma-20261001/**`. Read-only model/runtime metadata probes on `ai` are allowed; no credentials or user task data are read. An SSH loopback forward may carry these authorized requests to the existing service and must be closed afterward. Compare only with independent graders and report missing telemetry and deployment/provenance limits explicitly.

Owner continuation on 2026-09-30 authorizes concretizing the fresh calibration benchmark and verifying it offline. SL-1 owns a new, explicitly exposed development corpus under `research/evaluation/pilot/**`; preserve every earlier pilot input and result. SL-3 additionally owns `scripts/verify_calibration_benchmark.py` and `tests/verification/test_calibration_benchmark.py` to lint case/group identities and verify reference answers and intentionally defective controls with existing graders and the installed restricted Linux image. This work defines no production quality thresholds, uses no provider credentials or model calls, creates no holdout evidence and grants no spending or policy authority. Related implementation/review/documentation variants must share their component group.

Owner follow-up on 2026-09-30 declines paid Windows signing and authorizes continuing independent evaluator work. Keep the unsigned-launcher failure open as deferred compatibility evidence, with Smart App Control enabled. No Azure or certificate purchase is authorized. SL-2 implements a trusted, frozen recorded-comparison evaluator in `src/jevdrill/analysis.py` and `tests/promotion/test_recorded_evidence.py`; SL-1 supplies a read-only retained-observation accessor in the existing development runner. Bind dataset membership, related groups, baseline/candidate plans, source digests, execution time and durable policy exposure before grading. Pass anonymous output artifacts to a separately configured independent grader. No configured grader, calibration data, paid work or policy authority is supplied by public requests. Local fixtures prove software behavior only.

SL-1 also implements a bounded independent JavaScript grader in the existing development integration, with tests under `tests/experiments/**`. It receives separately configured input/answer recipes by opaque grading key, requires an explicit authorization callback and duration limit, uses the existing restricted Linux image and custody lock, and compares answers outside candidate code. Its rubric covers answer correctness only; input-preservation self-reports cannot establish a mandatory integrity requirement. This implementation and local synthetic-container proof confer no experiment spending or promotion authority. SL-0 permits the analysis module to reuse routing's existing candidate fingerprint function and regenerates the vocabulary document.

Owner continuation on 2026-09-30 accepts the recommended bounded BAML development adapter. Implement and verify it with local provider fixtures and the existing restricted container runtime. This does not replenish the original pilot ledger, authorize paid calls, or activate a policy. SL-1 additionally owns `baml_src/development.baml`, `src/jevdrill/integrations/development.py`, and `tests/experiments/test_development.py`. Submission persists work; an explicitly invoked trusted worker executes it. No scheduler is installed. Preserve the original pilot sources and results.

SL-1 also owns the optional custody-descriptor callback in `src/jevdrill/integrations/archive.py`, reusing the existing native lock for child-process custody without changing maintenance behavior. Linux development containers enforce an absolute deadline internally. Recovery must account for an interrupted container launch before asserting cleanup.

SL-3 additionally owns `scripts/verify_development_runtime.py` for explicit Linux verification against the already installed immutable image. It uses synthetic local HTTP responses and purpose-built code, records worker-death cleanup, and performs no paid calls or image pulls.

Owner follow-up on 2026-09-30 authorizes implementation in order: admission, execution/recovery, then governed policy updates. The first promoted policy may change only candidate ordering within an approved task group. Eligibility checks, caller constraints, permissions, required guidance and spending limits retain precedence. This authorizes implementation and offline verification; it does not activate a policy, expand the pilot budget or authorize new paid calls. SL-2 additionally owns `src/jevdrill/routing.py` and `tests/routing/test_routing.py` for applying this bounded ordering; shared persistence changes remain sequential with SL-1. Production rollout requires a separately configured promotion grant and trustworthy independent evaluation inputs.

Continue the verified LEARN phase in the existing task-owned worktree. The owner selected no additional critical failures, with other tolerances calibrated separately for implementation, review and documentation. Record this rule without inventing empirical thresholds. Previous native evidence proves its recorded inputs; changed inputs require new verification.

The owner enabled the development calibration pilot and approved a bounded BAML API adapter on 2026-09-29. Limits: two candidates, one experiment at a time, 120 seconds per experiment, 2 CPUs, 2 GiB, $1 raw cost per experiment and $5 across the whole pilot. Use purpose-built non-sensitive development tasks and already authorized providers only. No policy activation or external publication is authorized. Preserve prior HOST and LEARN changes.

## Interface Freeze Gates
- [ ] IF-0-EXPERIMENT-1 — BAML experiment request/result and policy evaluation contracts enforce durable transitions, scoped budgets, objective-specific critical-regression vetoes, predeclared calibration, recorded exposure and bounded rollback.

## Lane Index & Dependencies
SL-0 — Contracts and owner decision
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-3
  Parallel-safe: no

SL-1 — Scheduling and execution
  Depends on: SL-0
  Blocks: SL-2, SL-3
  Parallel-safe: no

SL-2 — Evaluation and policy lifecycle
  Depends on: SL-0, SL-1
  Blocks: SL-3
  Parallel-safe: no

SL-3 — Application, docs and evidence reducer
  Depends on: SL-0, SL-1, SL-2
  Blocks: (none)
  Parallel-safe: no

## Lanes
### SL-0 — Contracts and owner decision
- **Scope**: Freeze public experiment/evaluation contracts and record the accepted promotion rule.
- **Owned files**: `baml_src/contracts.baml`, `baml_src/boundary.json`, `schemas/**`, `src/baml_sdk/**`, `docs/vocabulary.yaml`, `docs/vocabulary.md`, `docs/contract-decisions.md`, `docs/evaluation-protocol.md`, `specs/jevdrill-design-input.md`, `evidence/CONTRACT/coverage.json`, `evidence/LEARN/promotion-decision.json`, `pyproject.toml`, `tests/contracts/fixtures/experiment.json`, `tests/contracts/test_experiment_contracts.py`
- **Interfaces provided**: `ExperimentRequest`, `ExperimentResult`, `ExperimentAuthorization`, `PolicyRequest`, `PolicyResult`, `QualityCalibration`, `PolicyEvaluation`
- **Interfaces consumed**: `ComparisonExperiment`, `ExperimentLimits`, `ExecutionEvent`, `CommandScope`, `OptimizationObjective` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Reject missing fields, coercion, undeclared fields, invalid bounds and mismatched scope through Python/Node shared fixtures.
  - impl: Generate strict schemas from BAML. Record owner rule and empirical calibration boundary.
  - verify: Generation, Python/Node parity, vocabulary/import checks.

### SL-1 — Scheduling and execution
- **Scope**: Persist deduplicated comparison proposals and enforce authority, reservations, context, contention, deadlines and cancellation.
- **Owned files**: `src/jevdrill/experiments.py`, `src/jevdrill/storage.py`, `src/jevdrill/integrations/experiments.py`, `src/jevdrill/integrations/pilot.py`, `src/jevdrill/integrations/development.py`, `src/jevdrill/integrations/archive.py`, `baml_src/pilot.baml`, `baml_src/review_pilot.baml`, `baml_src/development.baml`, `tests/integrations/test_pilot.py`, `scripts/run_calibration_pilot.py`, `research/evaluation/pilot/**`, `tests/experiments/**`, `tests/storage/test_experiments.py`
- **Interfaces provided**: `Experiments.handle`, `ExperimentRunner`, `RestrictedContainerRunner`, `experiment_storage`
- **Interfaces consumed**: `ExperimentRequest`, `ExperimentResult`, `ExperimentAuthorization`, `ComparisonExperiment` (pre-existing), `ExecutionEvent` (pre-existing), `CommandScope` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Deduplication, recurrence priority, disabled/missing/expired authority, concurrent reservations, daily caps, lost acknowledgments, deleted context, host contention, timeout/partial completion and unavailable runtime.
  - impl: Versioned deterministic priority; immutable proposal inputs; idempotent transactional reservations; controlled state transitions; internal restricted execution and host handoff. Preserve measurement provenance and separate host preference. Internal code receives copied inputs, no credentials/sockets/network, bounded resources and complete descendant cancellation.
  - verify: Targeted experiment/storage tests and actual restricted-runtime probe where available.
  - impl: Bounded BAML API pilot exception. Verify exact provider model snapshots, request shape, output cap and absence of retries against the pinned client. Reserve the provider context ceiling plus capped output at full raw rates; estimates alone cannot authorize calls. Persist reservations before dispatch and retain them on uncertain outcomes or restart. Test concurrency, timeout and malformed responses before live use. Preserve attributable usage, timing, model outputs and independent development checks for later reclassification.

### SL-2 — Evaluation and policy lifecycle
- **Scope**: Evaluate paired comparisons under recorded task-family calibration and govern scoped bounded policy rollout and rollback.
- **Owned files**: `src/jevdrill/evaluation.py`, `src/jevdrill/analysis.py`, `src/jevdrill/routing.py`, `tests/routing/test_routing.py`, `tests/promotion/**`, `tests/evaluation/test_policy_evaluation.py`, `tests/evaluation/test_review_scoring.py`
- **Interfaces provided**: `evaluate_policy`, `PolicyLifecycle`
- **Interfaces consumed**: `QualityCalibration`, `PolicyEvaluation`, `PolicyRequest`, `PolicyResult`, `experiment_storage`
- **Parallel-safe**: no
- **Tasks**:
  - test: Missing/late calibration, unblinded identities, exposed/release holdouts, missing outcomes, critical regressions despite average improvement, task-family quality floors, insufficient samples, uncertainty and objective reclassification.
  - impl: Preserve observations and calibration revisions; require independent checks, separate promotion authority and bounded scope. Record exposure before evaluation. Reject stale supporting evidence, suspend regressing versions and restore a currently verified previous policy or return non-ready. Deletion invalidates evidence without asserting regression.
  - verify: Construction-site negative controls through persistent policy lifecycle.

### SL-3 — Application, docs and evidence reducer
- **Scope**: Wire bounded CLI/application operations and document and verify production behavior.
- **Owned files**: `src/jevdrill/application.py`, `src/jevdrill/cli.py`, `tests/application/test_experiments.py`, `tests/cli/test_experiments.py`, `scripts/verify_experiment_phase.py`, `scripts/verify_development_runtime.py`, `scripts/verify_calibration_benchmark.py`, `scripts/run_local_calibration.py`, `tests/verification/test_local_calibration.py`, `tests/verification/test_calibration_benchmark.py`, `tests/verification/test_experiment_phase.py`, `docs/experiment-interfaces.md`, `docs/experiment-readiness.md`, `README.md`, `evidence/EXPERIMENT/**`
- **Interfaces provided**: `experiment`, `policy`, `experiment_native_verification`
- **Interfaces consumed**: `Experiments.handle`, `PolicyLifecycle`, `ExperimentResult`, `PolicyResult`
- **Parallel-safe**: no
- **Tasks**:
  - test: Real CLI dispatch, host handshake, durable retry and native reducer rejects stale/missing/skipped proof.
  - impl: Document exact implemented adapter support, live enablement limits, calibration process, recovery and remaining empirical evidence. Do not claim synthetic fixtures prove model quality.
  - verify: Full regression and native Linux/macOS/Windows matrix, generated outputs, package/type/lint checks.

## Verification
`automation.suite_command: uv run python scripts/verify_experiment_phase.py --reduce-only`

Narrow tests precede the full suite. Collect native evidence with `uv run python scripts/verify_experiment_phase.py --local-only`; reduction must require matching inputs and zero failures/skips. Preserve actual runtime availability results and all exit codes. Live holdout access and paid experiments remain disabled until specific limits and evaluation settings are recorded. Flag native collection over 300 seconds.

## Acceptance Criteria
- [ ] EC-EXPERIMENT-1 — proven by `tests/experiments` and `tests/storage/test_experiments.py`; falsified by disabled-authority and concurrent-budget controls entering production scheduling.
- [ ] EC-EXPERIMENT-2 — proven by `tests/experiments`, `tests/application/test_experiments.py` and `tests/cli/test_experiments.py` on native platforms; falsified by timeout, missing context, unsupported isolation, contention and side-effect rejection.
- [ ] EC-EXPERIMENT-3 — proven by `tests/promotion` and `tests/evaluation/test_policy_evaluation.py`; falsified by critical regression, stale/deleted evidence, exposed holdout and unauthorized promotion through production lifecycle.

## Spec Closeout Plan
- schema: `spec_delta_closeout.v1`
- decision: `roadmap_amendment`
- target surfaces: `docs/experiment-interfaces.md`, `docs/experiment-readiness.md`, `docs/evaluation-protocol.md`, `docs/contract-decisions.md`, `specs/jevdrill-design-input.md`
- evidence paths: `evidence/EXPERIMENT/spec-delta.json`, `evidence/EXPERIMENT/verification.json`
- redaction posture: `metadata_only`
- downstream handling: none

## Execution bounds and read access
Allow purpose-built local Gemma study outputs in `evidence/EXPERIMENT/local-gemma/**` and its persistent ledger/logs in `.phase-loop/runs/EXPERIMENT-gemma-20261001/**`. Only model/serving metadata from `ai` may be inspected, without credentials, raw logs or user tasks. The local model service remains unchanged.

Read repository code/docs/synthetic fixtures and metadata-only prior phase evidence. Runner logs and skill handoffs/reflections are allowed operational records. Allow runtime-only access to account `my`, `op://Consiliency Deploy Secrets/OpenAI/OPENAI_API_KEY`; never persist or print the credential. Allow purpose-built development inputs in `research/evaluation/pilot/**` and their provider responses and measured results in `evidence/EXPERIMENT/pilot/**`. Allow the pilot's persistent reservation database and operational logs under `.phase-loop/runs/EXPERIMENT-pilot-20260929/**`; every resume uses the same database. Host setup may restore the Node container image for this authorized pilot, then bind execution to its inspected immutable image ID. The product runner cannot pull images. No user task databases, private corpora or sealed release holdouts. Native task checkouts may receive task-owned snapshots. Existing agent-harness companion source is read-only until an exact companion-owned plan is recorded. No external publication or scheduler installation.

## Execution Notes
Execute sequentially; the two implementation lanes have contract and terminal reducer lanes. Stage planning artifacts, preserve earlier changes, and keep proof tied to exact inputs. Any unavailable required adapter or empirically uncalibrated promotion setting remains explicitly unverified; do not substitute fixtures for operational proof.
