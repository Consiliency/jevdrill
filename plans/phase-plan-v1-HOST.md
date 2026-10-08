---
phase_loop_plan_version: 1
phase: HOST
roadmap: specs/phase-plans-v1.md
roadmap_sha256: a5cbd9e6d924385cc6a2e286b394b1408fa5a568176cee74b8b40524466cc86a
---

# HOST: Harness integration and routing acceptance

> Replanning required: EC-HOST-4 adds the discovery-to-harness-to-task flow.
> Preserve this plan's prior evidence; revise after ROUTE interfaces freeze.
> Updating the roadmap hash alone is insufficient. See `docs/drill-roadmap-map.md`.

## Context

Implement the amended HOST scope against `docs/route-interfaces.md`, the accepted decisions, CONTRACT coverage and `docs/evaluation-protocol.md`. Canonical `.phase-loop/state.json` and the latest `manual_repair` ledger event agree that CONTRACT and ROUTE are complete and HOST is unplanned; live Git is clean. Historical pending prose in ROUTE evidence and manifest entries does not supersede that reconciliation.

The CLI already accepts strict `RouteInputs`, persists decisions/reports and exposes scoped replay/deletion. Notices exist in SQLite but have no retrieval path. Evaluation currently provides aggregation/split helpers and synthetic cases. The inspected host has launch construction and metrics, but no JEV Drill bridge. This plan adds the adapter/queue workstream through a separately owned host companion and the JEV Drill conformance/evaluation workstream; a shared preamble and terminal reducer support both.

## External Inputs

The original companion is preserved at `/mnt/workspace/worktrees/viperjuice/agent-harness-jevdrill-host` on `codex/jevdrill-host`. The integrated verification input is `/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port` on `codex/jevdrill-windows-port`, based on agent-harness revision `56dce95a52625a58cd08911f8f623c637bf52e44` (runtime source version 0.7.20). It combines the companion adapter with the separately planned Windows prerequisites. The parent owns companion planning and implementation under those repo-local plans. Do not duplicate that work or edit sibling source from this JEV lane. Record current source and packaged-resource digests in the handoff and native evidence; prior checkout evidence remains historical.

Explicit read inputs for required checks are `evidence/CONTRACT/coverage.json`, `evidence/CONTRACT/evaluation-protocol.json`, `evidence/CONTRACT/spec-delta.json`, `evidence/CONTRACT/verification.json`, `evidence/CONTRACT/platforms/*.json`, `evidence/ROUTE/*.json`, `evidence/ROUTE/platforms/*.json`, and the reviewed synthetic fixture `research/evaluation/cases.json`. These are metadata-only prior-phase evidence or synthetic test inputs; never treat prior-phase results as HOST acceptance. HOST-owned generated schemas, shared synthetic fixtures, evaluation inputs and metadata-only outputs may be read for this phase's verification. No private corpora, raw provider logs, credentials or holdout contents are authorized.

- Inspected agent-harness checkout: `/home/viperjuice/code/agent-harness`, at the external revision recorded in `specs/jevdrill-implementation-proposal.md` §4, source package `0.7.16`. Installed planning runtime is `0.7.19`; these are different inputs. Reinspect the assigned companion checkout and record actual compatibility before implementation; never assume installed/source parity.
- Preserve the CONTRACT pin `baml-language-0.20.1` / `baml-bridge==0.20.1` and CPython 3.13. New shared fixtures repeat Python/Node parity and native platform checks.
- Consumed upstream gates: IF-0-CONTRACT-1 and IF-0-ROUTE-1. No future output commit, merge topology or external release is prescribed.

## Interface Freeze Gates

- [ ] IF-0-HOST-1 — `RouteInputs` → validated `RoutingDecision` → existing host `build_launch_request` / `build_launch_spec` / `launch_with_spec`, with `ExecutionRun`, `ReportRequest` and durable `ReportAcknowledgment` semantics shared by main, delegated and lane paths; bounded host queue, notice retrieval and native/evaluation evidence satisfy all HOST ECs.
- [ ] IF-0-VC-2 — The effective suite below resolves actual commands, covers every HOST EC and rejects missing/stale companion, platform, evaluation or spec-closeout evidence; command collection alone cannot freeze HOST.

## Lane Index & Dependencies

SL-0 — Shared contract and companion preamble
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-3
  Parallel-safe: no

SL-1 — Adapter handoff, notices and queue conformance
  Depends on: SL-0
  Blocks: SL-2, SL-3
  Parallel-safe: no

SL-2 — Independent routing acceptance evaluation
  Depends on: SL-0, SL-1
  Blocks: SL-3
  Parallel-safe: no

SL-3 — Native verification and documentation reducer
  Depends on: SL-0, SL-1, SL-2
  Blocks: (none)
  Parallel-safe: no

## Cross-Repo Gates

`HOST-ADAPTER` is a required companion dependency, not an already-produced IF gate. SL-0 writes `evidence/HOST/adapter-handoff.json` with fixture/schema digests, inspected source version, exact ownership, commands and expected evidence. Create the companion's repo-local execution plan before sibling writes. Keep its worktree, dirty-path accounting and closeout separate; this plan's Owned files are exclusively JEV Drill paths. The JEV executor can start SL-0 and local SL-1 tests immediately, but cannot substitute mocks for the missing companion.

The companion owns these agent-harness-relative paths: `phase-loop-runtime/src/phase_loop_runtime/jevdrill_adapter.py`, `phase-loop-runtime/src/phase_loop_runtime/jevdrill_queue.py`, `phase-loop-runtime/src/phase_loop_runtime/runner.py`, `phase-loop-runtime/src/phase_loop_runtime/launcher.py`, `phase-loop-runtime/src/phase_loop_runtime/observability.py`, `phase-loop-runtime/tests/test_jevdrill_adapter.py`, `phase-loop-runtime/tests/test_jevdrill_queue.py`, `phase-loop-runtime/tests/fixtures/jevdrill/**`, `docs/jevdrill-integration.md`. Use standard-library queue/transport and explicit configuration arguments; no dependency or public host-model change is planned. Any additional file requires a companion ownership amendment first.

Hook `run_loop`, `launch_delegated_child` and `launch_harness_lane_work_unit` before final launch construction and after observed completion. Share one bridge/queue for hooks and explicit reporting. Preserve the resolved permission policy, governing overrides, worktree assignment, delegation budgets, CLI-only route restrictions and launch eligibility. Recheck actual model revision/access route/native effort/readiness; executor capability names and installed tools cannot establish inventory. Missing verified identity makes a candidate unavailable. Under JD-083, verified whole-run execution token limits are required only for requested spending, retry-spend or token ceilings; absent ceilings permit explicitly estimated-cost routing. Never infer provider usage from selected model metadata.

Build a strict `InventorySnapshot` with requested/resolved model identities, access route, native effort, freshness, counter revision and nullable price/rate revisions; pass catalog/settings snapshots and input/output planning estimates in `RouteInputs`. Preserve unknown rates/quality and raw versus adjusted cost. Readiness requires confirmed configured/runtime intersection and enforcement of any requested execution ceiling; estimates cannot establish that enforcement.

The companion freezes queue limits at 16 MiB, 10,000 records, 1 MiB per record and seven-day transport retention, with restrictive local permissions and bounded retry backoff. Overflow/expiry produces metadata-only delivery-loss notices and counters, never silent eviction or success. Redact credentials, excluded paths and hidden reasoning before SQLite/WAL persistence; store no raw tasks/outputs. Persist before sending; remove only on matching event ID with `accepted`/`duplicate` and `durable=true`. Conflicts, rejected/deleted tasks and corrupt records are visible terminal dispositions, not endless retries. Deletion cancels queued entries across producers within project/workspace, persists a tombstone before delivery can resume, and survives crash/restart.

Companion verification from its root: `uv run --project phase-loop-runtime pytest phase-loop-runtime/tests/test_jevdrill_adapter.py phase-loop-runtime/tests/test_jevdrill_queue.py phase-loop-runtime/tests/test_phase_loop_launcher.py phase-loop-runtime/tests/test_phase_loop_work_unit_observability.py`. Native platform collection additionally invokes the actual JEV CLI with the shared fixtures. The companion returns source/fixture digests, runner identity, command/assertion results and construction-site traces; SL-3 imports only redacted evidence. A missing companion is a repairable dependency, never a reason to omit EC-HOST-1/2.

## Lanes

### SL-0 — Shared contract and companion preamble

- **Scope**: Freeze additive notice transport and shared host fixtures before either workstream changes behavior.
- **Owned files**: `baml_src/contracts.baml`, `baml_src/boundary.json`, `schemas/**`, `src/baml_sdk/**`, `src/jevdrill/contracts.py`, `docs/vocabulary.yaml`, `docs/vocabulary.md`, `docs/host-interfaces.md`, `pyproject.toml`, `uv.lock`, `tests/contracts/test_host_contracts.py`, `tests/contracts/fixtures/host.json`, `evidence/HOST/adapter-handoff.json`
- **Interfaces provided**: `host_fixture_contract`, `notice_query_contract`, `companion_handoff`
- **Interfaces consumed**: `RouteInputs`, `ExecutionRun`, `ReportRequest`, `LocalNotice`, `CommandScope` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add shared positive/negative fixtures for all five routing outcomes, acknowledgment identity/durability, selected/applied substitutions, retry links, missing telemetry, dry runs, capability mismatch and notice scope. Python and Node must reject unknown fields, coercion and unsupported versions identically.
  - impl: Add BAML-authored `NoticeRequest { schema_version: "1", scope: CommandScope }` and `NoticeInbox { schema_version: "1", notices: LocalNotice[] }`; register exports in boundary metadata and regenerate schemas/SDK with `uv run python scripts/check_generated_contracts.py --write`. Freeze `jevdrill --storage PATH notices` taking NoticeRequest on stdin. Preserve existing shapes; the read-only query neither deletes notices nor grants management authority.
  - impl: Extend `StoragePort` with scoped notice retrieval, register vocabulary and include conformance tests in pytest discovery. Author host fixtures from BAML-derived schemas, not a duplicate handwritten field catalog. Freeze queue/CLI bounds, version negotiation, inventory provenance and handoff format in `docs/host-interfaces.md`.
  - impl: Handoff includes configured declarations from `.jevdrill/harnesses.yaml` and ignored machine overrides; intersect configured/runtime permission sets. Include positive path-entered controls and stale/forged inventory negatives. Specify unsupported resolution advice without setup or permission expansion.
  - verify: `uv run pytest tests/contracts/test_host_contracts.py tests/contracts/test_boundaries.py tests/contracts/test_generation.py`; `node scripts/contract_consumer.mjs tests/contracts/fixtures`; `uv run python scripts/check_generated_contracts.py`; `uv run python scripts/check_import_boundaries.py`.

### SL-1 — Adapter handoff, notices and queue conformance

- **Scope**: Complete JEV notice delivery and exercise the separately implemented host bridge through production launch and transport paths.
- **Owned files**: `src/jevdrill/application.py`, `src/jevdrill/cli.py`, `src/jevdrill/storage.py`, `tests/application/test_host_notices.py`, `tests/cli/test_host_notices.py`, `tests/storage/test_host_notices.py`, `tests/conformance/**`
- **Interfaces provided**: `host_conformance`
- **Interfaces consumed**: `host_fixture_contract`, `notice_query_contract`, `companion_handoff`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `test_launch_paths.py`, `test_transport_queue.py` and `test_notices.py` under conformance; invoke the installed CLI and companion production functions with controlled executor subprocesses. Require an entry witness for each main/delegated/lane construction path before fault injection. An absent companion fails integration tests, never skips them.
  - impl: Implement scoped notice retrieval using the existing notices table; materialize stable LocalNotice IDs and sanitized summaries. Wire the CLI query and all routing response notice fields without mutating replayed decisions. Fetch pending notices on every host connection, including explicit reporting; local notices remain visible across disconnects and repeated reads. Preserve project/workspace isolation and deletion.
  - impl: Complete HOST-ADAPTER handoff. Measure monotonic time before spawning; pass `--remaining-budget-ms` after accrued host overhead and enforce the same outer five-second routing deadline through startup, validation and durable decision. Bound request/response bytes; use argv/stdin without shell interpolation. Cancellation kills/reaps owned processes on all three OSes.
  - impl: Apply only ready plans under existing authority; bind selected/applied identities and reasons. Propagate recursion bypass into routing work itself. Retry after lost stdout uses the same key; intentional rerouting uses a new run linked through bounded failure context. Required guidance remains intact; optional guidance is injected once by revision/hash, deactivated at task end, and unsupported cleanup is reported.
  - test: Exercise permission narrowing, stale readiness, unknown prices, unenforceable token caps, malformed output, disconnect/recovery, duplicate/conflicting acknowledgments, reordered/corrected reports, crash windows, queue limits and cross-producer deletion races. Secret sentinels must be absent from queue DB/WAL and exported evidence. Dry-run completion never counts as accepted execution; preferences cannot overwrite checks; unknown usage retains its missing reason.
  - verify: `uv run pytest tests/conformance tests/application/test_host_notices.py tests/cli/test_host_notices.py tests/storage/test_host_notices.py`; run the companion command above and require HOST-ADAPTER evidence.

### SL-2 — Independent routing acceptance evaluation

- **Scope**: Evaluate the integrated routing path on predeclared development/validation cases with independent correctness/privacy checks and honest uncertainty.
- **Owned files**: `src/jevdrill/evaluation.py`, `tests/evaluation/test_host_acceptance.py`, `research/evaluation/host/**`, `evidence/HOST/evaluation.json`
- **Interfaces provided**: `host_evaluation`
- **Interfaces consumed**: `host_fixture_contract`, `host_conformance`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add independent implementation tests, review defect/false-positive/severity rubrics and documentation fact/coverage/reference/example checks. Negative controls through routed execution reject a broken implementation, missed critical defect, false documentation claim, privacy leak and swapped split assignment.
  - impl: Before candidate evaluation, version case groups, evaluators, thresholds, sample requirements and exposure records under `research/evaluation/host/`. Development and validation groups cannot share repository/template ancestry. Freeze mandatory correctness/privacy checks at all-required-checks passing; report denominators and uncertainty for measured metrics. Empirical quality/performance thresholds remain pending calibration where evidence cannot justify them.
  - impl: Run paired fixed-default, cheapest-feasible, no-optional-guidance and previous-policy baselines, plus retrieval where applicable, through the integrated path. Record reasoned not-applicable results; never invent a previous policy. Include routing startup/overhead, failed attempts, model/effort/guidance/source revisions and missing measurements. Synthetic executor cases establish bounded conformance only; comparative performance remains insufficient-evidence without suitable observed runs and predeclared budgets.
  - impl: Keep objective checks, model judgments and host preference separate. Record exposure without opening policy or release holdouts. Emit metadata-only evaluation results with explicit claim eligibility; sample insufficiency blocks gains/promotion claims and cannot excuse failed correctness/privacy acceptance.
  - verify: `uv run pytest tests/evaluation tests/conformance/test_launch_paths.py`.

### SL-3 — Native verification and documentation reducer

- **Scope**: Reduce every producer and companion result into HOST acceptance, fresh platform evidence and operator documentation.
- **Owned files**: `scripts/verify_host_phase.py`, `tests/verification/test_host_phase.py`, `.github/workflows/host.yml`, `evidence/HOST/platforms/**`, `evidence/HOST/companion/**`, `evidence/HOST/verification.json`, `evidence/HOST/coverage.json`, `evidence/HOST/spec-delta.json`, `docs/host-readiness.md`, `README.md`
- **Interfaces provided**: `host_verification`
- **Interfaces consumed**: `host_fixture_contract`, `notice_query_contract`, `companion_handoff`, `host_conformance`, `host_evaluation`
- **Parallel-safe**: no
- **Tasks**:
  - test: Reducer negatives reject absent/duplicate platforms, mismatched companion/schema/source digests, unentered launch paths, skipped assertions, forged success, missing EC coverage, stale evaluation, holdout exposure and malformed spec-delta. Aggregate failures without fail-fast truncation.
  - impl: Follow `verify_route_phase.py` collection/reduction patterns. Add default full, `--local-only` and `--reduce-only` modes; resolve companion checkout from `--agent-harness PATH` or `JEVDRILL_AGENT_HARNESS_ROOT`. Missing configuration/evidence fails closed. Native Linux/macOS/Windows CPython 3.13 jobs collect actual CLI/queue cancellation, locking/path/recovery and Python/Node parity results. Preserve earlier phase evidence; recollect HOST inputs when content changes.
  - impl: Record runner identity, OS/architecture, versions, command/input/output digests, assertion counts, duration and production-path witnesses. Reduce metadata in verification.json, covering all HOST ECs and IF-0-VC-2. Include independent evaluation and companion manifests; mock-only results cannot satisfy host wiring or platform claims.
  - impl: Write coverage for HOST decisions and inherited deferrals, plus spec_delta_closeout.v1. Update readiness/README with queue recovery/limits, notice behavior, compatibility, permission limitations, evidence gaps and LEARN handoff. No ratified-review, performance, adoption or publishing claims without their evidence.
  - verify: `uv run pytest tests/verification/test_host_phase.py`; `uv run python scripts/verify_host_phase.py`.

## Execution Notes

JD-084 (user approved 2026-09-29) changes macOS leased acceptance: reject native
leased launch before executor startup/lease transfer and supply the Linux-worker
resolution. Keep ordinary macOS execution local. Linux remains responsible for
proving leased descendant cleanup. Record native macOS rejection as its own
assertions; never relabel Linux worker proof as native macOS containment.

Execute serially; no subagents or writable fanout are authorized. Ownership is disjoint including generated outputs, fixtures and evidence. A separate scheduler-assigned host worktree must follow the team-host/workspace convention. No sibling edits occur under a JEV-owned lane. No UI/avatar/media render is a deliverable; notices are textual CLI/host output.

Preserve CLI/operator overrides, phase-plan policy, roadmap policy, executor-only Dispatch Hints, then registry defaults. No new model/effort policy or silent downgrade is introduced. Contract behavior changes beyond the additive notice surface require an explicit plan/spec amendment before downstream reliance.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `roadmap_amendment` (JD-083 under `plans/detailed-estimated-cost-routing-20260929.md`; JD-084 under the amended companion plan)
- target surfaces: `docs/host-interfaces.md`, `baml_src/contracts.baml`, `docs/vocabulary.yaml`
- evidence paths: `evidence/HOST/spec-delta.json`, `evidence/HOST/verification.json`, `evidence/HOST/coverage.json`
- redaction posture: `metadata_only`
- downstream handling: `none`

The notice query completes already-required inbox behavior; record its additive compatibility evidence. JD-083 amends execution-ceiling behavior and adds optional whole-run token bounds; its verification is recorded separately from incomplete HOST acceptance. Missing/malformed evidence is a non-human contract_bug.

## Verification

`automation.suite_command: uv run python scripts/verify_host_phase.py`

New commands/files above are implementation deliverables. Before handoff validation, IF-0-VC-2 binds each command to its producer and EC. During execution, preflight locked Python dependencies, Node/npm ci, the pinned BAML compiler and assigned companion path. No application tests/builds are run merely to author this plan.

After targeted lane tests, the suite aggregates `uv run pytest`, `python3 -m unittest discover -s tests -p 'test_catalog_*.py'`, Python/Node contract parity, generated/vocabulary/import checks, scoped Ruff checks, `uv run mypy src/jevdrill`, `uv build`, installed-package CLI tests, companion tests and evaluation reduction. Scope lint to production and phase tests as ROUTE does. Native collection uses `uv run python scripts/verify_host_phase.py --local-only --agent-harness PATH`; final reduction uses `uv run python scripts/verify_host_phase.py --reduce-only`. Local-only success never represents the three-platform gate.

Operational evidence must name its producing command/runner and content digest. Proxy evidence requires a runner-stamped roadmap amendment; this plan authorizes no such substitution. Flag proof-cost findings for single-node evaluation exceeding roughly five minutes or inability to report multiple failures.

## Acceptance Criteria

- [ ] EC-HOST-1 — proven by `uv run pytest tests/conformance/test_launch_paths.py` plus HOST-ADAPTER construction-site evidence; falsified by `test_permission_expansion_is_rejected` entering the real host launch constructor before asserting forbidden permission/model application prevents launch, with a permitted-path positive control.
- [ ] EC-HOST-2 — proven by `uv run pytest tests/conformance/test_transport_queue.py tests/conformance/test_notices.py` plus companion native queue evidence; falsified by `test_ack_loss_redaction_and_scoped_delete` entering production enqueue/report delivery, dropping the durable acknowledgment and asserting no duplicate accepted event, secret retention or deleted-task resurrection.
- [ ] EC-HOST-3 — proven by `uv run pytest tests/evaluation/test_host_acceptance.py` and `uv run python scripts/verify_host_phase.py --reduce-only`; falsified by `test_routed_bad_candidate_fails_independent_checks` entering the integrated routing/launch/evaluation path and `test_missing_platform_or_holdout_exposure_blocks` entering the production reducer before asserting rejection.

Close HOST only after both IF gates above pass with fresh evidence. Planning produces neither gate. Report implementation verification separately from plan validation; outstanding companion or evidence work must remain explicit.
