---
phase_loop_plan_version: 1
phase: HOST
roadmap: specs/phase-plans-v1.md
roadmap_sha256: 06fc6fc0c3f4e6e2bda5e45f6e82130f5780db1a5dd052e1377126d21ea859f0
---

# HOST: Harness integration and routing acceptance

## Context

Replace the superseded HOST scope with EC-HOST-1–4 from the roadmap. ROUTE now implements progressive discovery, linked route-v2, durable reservations/recovery and replay/deletion. Its current native report passes; its owned implementation diff remains uncommitted in this worktree. Preserve that baseline and every unrelated preserved worktree. This plan neither authorizes publication nor requires a future commit/merge topology.

Preserved HOST work provides notice retrieval, queue/transport, launch hooks and evaluation scaffolding. It has no discovery/decomposition handoff, validates only RouteInputs, and uses fixed witness counts and some hard-coded success flags. Reuse reviewed functions and public synthetic fixtures selectively; never copy entire modified application/storage/contracts/evaluation files containing LEARN or EXPERIMENT work. Historical reports establish no amended HOST criterion. This is a planner self-reviewed plan, not ratified cross-vendor review.

## External Inputs

- Inspected agent-harness integration input: /mnt/workspace/worktrees/viperjuice/agent-harness-windows-port; HEAD 56dce95a52625a58cd08911f8f623c637bf52e44, source package 0.7.20, with preserved uncommitted adapter/platform work. Earlier companion: /mnt/workspace/worktrees/viperjuice/agent-harness-jevdrill-host; HEAD 71fcad8690a68dba73ef3979def0e9fc3e18bba2. These are inspected external inputs, not required future output commits.
- Supported construction sites: runner.run_loop, launch_delegated_child, launch_harness_lane_work_unit; launcher.build_launch_request, build_launch_spec, launch_with_spec; JevDrillAdapter, JevDrillTransport and ReportQueue. Installed planning tooling is a separate environment.
- Preserve BAML language/bridge 0.20.1 and JEV CPython 3.13. Companion and JEV environments remain separate. Native Windows uses the installed JEV interpreter with -m jevdrill.cli.
- Read inputs: public source/tests/docs/config in these assigned checkouts; strict generated schemas; evidence/CONTRACT/*.json, evidence/CONTRACT/platforms/*.json, evidence/ROUTE/*.json and evidence/ROUTE/platforms/*.json as metadata only. Public synthetic recovery inputs are research/evaluation/cases.json and research/evaluation/host/{protocol.json,test_bridge_probe.py,test_baseline_probe.py} in the preserved JEV worktree. No other research corpus, holdout, credentials, raw provider logs, ignored machine overrides or .pipeline input is authorized.
- Historical companion regression fixtures requiring an ancestor dotfiles checkout must be scoped by the companion plan to tracked public bootstrap/config/helpers and an exact runtime snapshot; do not run bootstrap or read private settings.

## Interface Freeze Gates

- [x] IF-0-HOST-1 — Installed discover → validated DiscoveryResult → harness planning/decomposition → at least two DiscoveryRouteInputs tasks → independently validated RoutingDecision → existing launch constructors → ExecutionRun/ReportRequest/durable acknowledgment; one bounded queue, notice retrieval, guidance lifecycle and native independent checks satisfy all four HOST ECs.
- [x] IF-0-VC-2 — scripts/verify_host_phase.py resolves the actual commands and consumes executed control identities/outcomes, source/schema/fixture digests, companion receipts and native evidence. Three-criterion, route-v1-only, skipped or fabricated-witness reports reject. This is a verification obligation, not an additional HOST-produced roadmap gate.

### Objective and task handoff

Extend the companion with JevDrillAdapter.discover_objective(inputs, *, started_at=None), returning the strict DiscoveryResult through JevDrillTransport.call("discover", inputs). Only selected_guidance and no_optional_guidance permit linked task routing. Other outcomes return structured remediation and start no routed executor.

The harness consumes selected instructions transiently for its ordinary planning/decomposition path. Drill never manufactures the task list. Existing host plan/lane/task construction supplies stable task IDs. inputs_for(context) remains the trusted host callback: bound contexts return DiscoveryRouteInputs version 2 with unchanged nested RouteInputs and the exact stored DiscoveryRef. Unbound legacy tasks retain explicit route-v1 compatibility; they cannot satisfy EC-HOST-4.

Persist only project/workspace/producer, work_objective_id, discovery_id, trace_digest and task/decision/run linkage in the host binding ledger. Never persist objective text, returned instructions, decomposition prompts or raw outputs there. Recheck the stored discovery through inspect-discovery before linked launch, plus queue tombstones and current authorized catalog/revisions. A forged reference, changed revision or deletion prevents launch. Retry after lost stdout retains the same discovery key and allowance; intentional rediscovery uses a distinct key without resurrecting a deleted objective.

Each logical discover or route operation has its own spawn-inclusive five-second deadline and 1,000,000-byte request/response bounds. Attached notice queries share that operation's budget. Decomposition and execution have separate host budgets; two later task routes do not share a fabricated five-second objective-wide deadline. Preserve recursion bypass inside routing work, kill/reap canceled CLI children, and never launch from partial output.

Trusted host policy may retain its current model by narrowing verified inventory to that identity before selection, or decline a returned recommendation without starting a routed run. Declines/preferences remain separate from correctness and execution success. Apply validates the selected plan; never mutate selected identities to invent an applied plan. Operator/policy overrides, permissions, worktrees, delegation budgets and CLI route restrictions remain authoritative.

Guidance is scoped to concrete tasks/runs, not a global per-objective injected flag. Decomposition guidance must not leak into unrelated execution prompts. Each applied optional revision/hash is injected once into a fresh task prompt; retries cannot append it again. Required guidance is retained. Cleanup restores task-local prompt state and emits guidance_deactivated, or reports the host limitation.

### Queue and management handoff

Retain one ReportQueue for hooks and explicit reporting: 16 MiB serialized payload, 10,000 records, 1 MiB per record, seven-day transport retention, restrictive native permissions and bounded backoff. Sanitize before DB/WAL writes. Remove only after matching event ID and accepted/duplicate with durable=true. Conflict/rejection, overflow/expiry and corruption remain visible terminal dispositions; delivery failure cannot replace executor results.

Add durable project/workspace/work_objective_id tombstones across producers. Serialize deletion with discovery binding, preparation and final launch; commit the local tombstone before delete-discovery transport and keep it after lost responses. Objective deletion prevents future linked execution but does not erase independent task report records or fabricate task deletion. Existing delete_task retains its distinct report-cancellation semantics.

Add BAML NoticeRequest { schema_version: "1", scope: CommandScope } and NoticeInbox { schema_version: "1", notices: LocalNotice[] }. Freeze StoragePort.load_notices(scope), Application.notices(payload) and stdin-based jevdrill --storage PATH notices. Scope is project/workspace; producer identity grants no wider authority. Reads do not acknowledge/delete notices. Fresh decisions snapshot current notices before commit; retries/replay remain immutable. Every host connection, including explicit reporting, queries pending notices.

## Cross-Repo Gate

HOST-ADAPTER is a separate agent-harness workstream. SL-0 emits evidence/HOST/adapter-handoff.json with exact schemas/fixtures, API signatures, digest inputs and required controls. Before sibling source writes, revise its repo-local companion plan in an isolated assigned worktree; record ownership and preserve unrelated dirty work. This JEV plan owns no sibling path and authorizes no installed-runtime change.

Companion ownership must cover phase-loop-runtime/src/phase_loop_runtime/{jevdrill_adapter,jevdrill_queue,runner,launcher,observability}.py, matching adapter/queue/launcher/observability tests, dedicated discovery tests, tests/fixtures/jevdrill/** and docs/jevdrill-integration.md. Include touched public declarations, platform helpers and tests only through an explicit companion amendment. Existing serial dispatch stays serial; no new concurrency or provider/host implementation.

Require content-bound native companion receipts before terminal HOST reduction. Missing companion configuration fails integration tests rather than skipping. JEV SL-0/local notice work may proceed while the companion is prepared; missing discovery support cannot be replaced by injected selected skills.

## Lane Index & Dependencies

- SL-0 — Contracts and companion preamble; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 — Notices and installed CLI; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 — Discovery and launch conformance; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 — Independent evaluation; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 — Evidence/documentation reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: (none); Parallel-safe: no

## Lanes

### SL-0 — Contracts and companion preamble

- **Scope**: Freeze additive notice contracts and discovery-aware companion fixtures.
- **Owned files**: `baml_src/contracts.baml`, `baml_src/boundary.json`, `schemas/**`, `src/baml_sdk/**`, `src/jevdrill/contracts.py`, `docs/vocabulary.yaml`, `docs/vocabulary.md`, `docs/host-interfaces.md`, `pyproject.toml`, `uv.lock`, `tests/contracts/test_host_contracts.py`, `tests/contracts/fixtures/host.json`, `scripts/contract_consumer.mjs`, `evidence/HOST/adapter-handoff.json`
- **Interfaces provided**: host_fixture_contract, notice_query_contract, companion_handoff
- **Interfaces consumed**: pre-existing DiscoveryInputs, DiscoveryResult, DiscoveryRef, DiscoveryRouteInputs, RouteInputs, RoutingDecision, ExecutionRun, ReportRequest/Acknowledgment, LocalNotice, CommandScope
- **Parallel-safe**: no
- **Tasks**:
  - test: Shared positive/negative fixtures cover five discovery statuses, five route statuses, spoofed/scope-mismatched references, strict notices, acknowledgments, declines, substitutions and missing telemetry. Preserve v1/v2 fixtures and Python/Node parity.
  - impl: Add notice types/exports and StoragePort method; regenerate normally. Declare canonical host terms/import permissions. Register conformance tests without importing later-phase suites. Dependency versions remain unchanged unless an amendment documents a real need.
  - impl: Write the companion handoff and fresh companion-plan prerequisite; include configured/runtime intersection, trusted callbacks, binding/tombstone ledger and exact management response validation. Do not read ignored overrides implicitly.
  - verify: `uv run pytest tests/contracts`; `node scripts/contract_consumer.mjs tests/contracts/fixtures`; `uv run python scripts/check_generated_contracts.py`; `uv run python scripts/render_vocabulary.py --check`.

### SL-1 — Notices and installed CLI

- **Scope**: Complete scoped notice delivery without changing immutable discovery or route records.
- **Owned files**: `src/jevdrill/application.py`, `src/jevdrill/cli.py`, `src/jevdrill/storage.py`, `tests/application/test_host_notices.py`, `tests/application/test_application.py`, `tests/application/test_route_integration.py`, `tests/cli/test_host_notices.py`, `tests/storage/test_host_notices.py`
- **Interfaces provided**: notice_delivery
- **Interfaces consumed**: notice_query_contract, host_fixture_contract, existing ROUTE SQLite lifecycle
- **Parallel-safe**: no
- **Tasks**:
  - test: Scope isolation, repeated reads, fresh/cached decision snapshots, immutable retry/replay, deleted tasks, deadline/output bounds and installed native command paths.
  - impl: Adapt the preserved notice functions to current ROUTE tables and transaction boundaries; do not import LEARN lifecycle tables/migrations. Use stable sanitized LocalNotice identities. Wire CLI/application before durable decision commit.
  - verify: `uv run pytest tests/application/test_host_notices.py tests/cli/test_host_notices.py tests/storage/test_host_notices.py tests/application/test_application.py tests/application/test_route_integration.py`.

### SL-2 — Discovery and launch conformance

- **Scope**: Exercise installed discovery, real harness decomposition/task construction and all three launch/queue paths.
- **Owned files**: `tests/conformance/**`, `research/evaluation/host/test_bridge_probe.py`
- **Interfaces provided**: host_conformance, discovery_handoff_witnesses
- **Interfaces consumed**: host_fixture_contract, notice_delivery, companion_handoff, separately produced HOST-ADAPTER
- **Parallel-safe**: no
- **Tasks**:
  - test: Add test_discovery_handoff.py beside launch/transport/notice tests. Positive flow must call installed CLI main/open_application, production discover/next_question, harness planning/decomposition and two distinct task constructions before route-v2 and actual launch constructors. Loopback may replace the external generated observation function, never Application, navigation, discovery results or task refs. Normal installed module smoke also runs.
  - test: Record entered path before fault injection. Controls cover false initial categories/useful alternates, unsuitable leaves, uncertain success/no-guidance/failures, objective-dependent guidance, independently eligible models/efforts, retain/decline, mandatory guidance, retry/deactivation and parent context leakage.
  - test: Exercise forged/deleted/stale references, relaxed inherited constraints, cancellation, unknown/enforcement-limited pricing, dry runs, recursion bypass, permission expansion, ACK loss/conflict, correction/reordering, queue limits, DB/WAL sentinels and deletion crashes/races across producers.
  - impl: Recover reviewed synthetic probes and replace fixed counts/boolean witnesses with identities and receipts from actual construction/transport events. Companion failures remain failures; preserve JD-084 native macOS early leased rejection and Linux cleanup proof.
  - verify: `uv run pytest tests/conformance`; companion command specified below.

### SL-3 — Independent evaluation

- **Scope**: Evaluate routed implementation/review/documentation artifacts using predeclared independent development/validation checks.
- **Owned files**: `src/jevdrill/evaluation.py`, `tests/evaluation/test_host_acceptance.py`, `research/evaluation/host/protocol.json`, `research/evaluation/host/test_baseline_probe.py`, `evidence/HOST/evaluation.json`
- **Interfaces provided**: host_evaluation
- **Interfaces consumed**: host_fixture_contract, host_conformance, discovery_handoff_witnesses, docs/evaluation-protocol.md
- **Parallel-safe**: no
- **Tasks**:
  - test: Reject routed broken implementations, missed critical defects, false documentation claims, privacy leaks and split leakage through entered production paths; include permitted positive controls and independent evaluator provenance.
  - impl: Freeze synthetic dataset/rubric revisions, ancestry-grouped splits, denominators and all-required correctness/privacy checks before exposure. Pair fixed-default, cheapest-feasible, no-optional-guidance and previous-policy baselines; retrieval where applicable. Explain unavailable baselines instead of inventing policy.
  - impl: Record discovery/routing/startup/reporting/evaluation overhead, task/decision/run/ref links, revisions, failed-attempt costs, unknown counters and uncertainty. Separate objective checks, model judgments and host preferences. Synthetic conformance proves software behavior; empirical floors/gains remain insufficient-evidence pending Q-12/Q-13 and authorized live budgets. Do not open any holdout.
  - verify: `uv run pytest tests/evaluation tests/conformance/test_discovery_handoff.py tests/conformance/test_launch_paths.py`.

### SL-4 — Evidence/documentation reducer

- **Scope**: Reduce every producer and companion receipt into native HOST acceptance and truthful documentation.
- **Owned files**: `scripts/verify_host_phase.py`, `tests/verification/test_host_phase.py`, `.github/workflows/host.yml`, `evidence/HOST/platforms/**`, `evidence/HOST/companion/**`, `evidence/HOST/verification.json`, `evidence/HOST/coverage.json`, `evidence/HOST/spec-delta.json`, `evidence/HOST/closeout.json`, `evidence/HOST/history/**`, `docs/host-readiness.md`, `README.md`
- **Interfaces provided**: host_verification
- **Interfaces consumed**: host_fixture_contract, notice_query_contract, companion_handoff, notice_delivery, host_conformance, discovery_handoff_witnesses, host_evaluation
- **Parallel-safe**: no
- **Tasks**:
  - test: Reject old three-criterion reports, route-v1-only witnesses, missing/failed/skipped controls, forged success flags, duplicate/stale native inputs, wrong commands, mismatched packaged companion/schema resources, missing decomposition/two-task links, exposed holdouts and malformed coverage/spec-delta.
  - impl: Adapt collect/reduce patterns with --local-only, --reduce-only and --agent-harness PATH. Bind JEV and companion inputs before/after collection using portable path ordering. Record runner/OS/version, command/output hashes and executed parameterized test identities/outcomes. Link entry witnesses to actual successful assertions and trace metadata; constants cannot substitute.
  - impl: Collect native Linux/macOS/Windows with separate installed environments. Full command manifest covers all HOST ECs, inherited ROUTE controls, generation, Python/Node parity, privacy/recovery and independent evaluation. Preserve prior-phase evidence; current ROUTE regressions live in HOST receipts rather than rewriting evidence/ROUTE. Archive recovered historical HOST reports before reduction.
  - impl: Write HOST coverage/spec-delta/readiness, queue/discovery recovery and LEARN replanning handoff. No publication, adoption, ratified-review, live quality or savings claim follows from synthetic passing checks.
  - verify: `uv run pytest tests/verification/test_host_phase.py`; `uv run python scripts/verify_host_phase.py --agent-harness PATH`.

## Verification

Effective automation.suite_command: `uv run python scripts/verify_host_phase.py`. Resolve --agent-harness PATH or JEVDRILL_AGENT_HARNESS_ROOT explicitly; missing configuration fails closed. Native companion interpreter can be supplied with JEVDRILL_AGENT_HARNESS_PYTHON. New commands/tests are implementation deliverables.

Companion suite from its root: `uv run --project phase-loop-runtime --group test pytest phase-loop-runtime/tests/test_jevdrill_adapter.py phase-loop-runtime/tests/test_jevdrill_queue.py phase-loop-runtime/tests/test_jevdrill_discovery.py phase-loop-runtime/tests/test_phase_loop_launcher.py phase-loop-runtime/tests/test_phase_loop_work_unit_observability.py`.

After targeted tests, aggregate all scoped JEV pytest tests, retained catalog checks, locked dependency setup, Node parity, pinned generation, vocabulary/import checks, scoped Ruff/mypy, build/installed-package checks and companion assertions. Native collection: `uv run python scripts/verify_host_phase.py --local-only --agent-harness PATH`; final reduction: `uv run python scripts/verify_host_phase.py --reduce-only`. A local pass cannot close the matrix. Preserve the 600-second collector bound and flag proof exceeding five minutes; product calls remain five seconds. Planning runs no product tests/builds.

## Acceptance Criteria

- [x] EC-HOST-1 — proven by `uv run pytest tests/conformance/test_launch_paths.py tests/conformance/test_discovery_handoff.py` and companion assertions; falsified by entered permission-expansion, stale readiness, retry double-injection or dry-run-success controls.
- [x] EC-HOST-2 — proven by `uv run pytest tests/conformance/test_transport_queue.py tests/conformance/test_notices.py tests/storage/test_host_notices.py`; falsified by entered ACK-loss/redaction/cross-producer deletion controls and their crash/restart variants.
- [x] EC-HOST-3 — proven by `uv run pytest tests/evaluation/test_host_acceptance.py` and the native reducer; falsified by independently rejected routed artifacts, split leakage, holdout exposure or ineligible performance claims.
- [x] EC-HOST-4 — proven by `uv run pytest tests/conformance/test_discovery_handoff.py` and the native reducer; falsified by injected preselected references, absent harness decomposition, one task only, forced identical eligible configurations, ignored retain/decline or deleted objective reuse.
- [x] IF-0-VC-2 — proven by `uv run pytest tests/verification/test_host_phase.py` and `uv run python scripts/verify_host_phase.py --reduce-only`; falsified by old/missing/stale/constant-only acceptance evidence.

## Execution Notes

Execute serially; no subagents, sibling edits or writable fanout under these JEV lanes. Control-plane plan/manifest/handoff writes are separate from lane source ownership. Inspect current source compatibility and dirty ownership before companion execution; isolate preserved work rather than overwrite it. Default-disabled integration remains explicit. JD-083 preserves estimated-cost routing without requested ceilings, and requires verified whole-run token/spending enforcement when requested. JD-084 keeps ordinary macOS execution local and rejects leased macOS startup with configured-Linux-worker resolution; no silent forwarding.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `roadmap_amendment`
- target surfaces: `docs/host-interfaces.md`, `baml_src/contracts.baml`, `docs/vocabulary.yaml`
- evidence paths: `evidence/HOST/spec-delta.json`, `evidence/HOST/verification.json`, `evidence/HOST/coverage.json`
- redaction posture: `metadata_only`
- downstream handling: `replan_LEARN`

Preserve accepted JD-083/084; document additive discovery handoff/notice compatibility. Amend the roadmap only for a demonstrated uncovered behavior, never to relax EC-HOST-1–4. Planning produces no IF gate.
