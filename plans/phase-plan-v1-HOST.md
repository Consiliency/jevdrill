---
phase_loop_plan_version: 1
phase: HOST
roadmap: specs/phase-plans-v1.md
roadmap_sha256: 4ecbf27188b634d6ea5346cd67d61ab36d50d3ad0416a9a6d0d2602bb2698ab8
---

# HOST: Harness integration and routing acceptance

> Review status: draft written by Claude Opus 5.5. Board: a Fable 5.2 president
> with three seats (correctness; security and privacy; alternate vendor).
> Rounds: one, and a confirmation of its fixes. Pull request:
> Consiliency/jevdrill#89; amended by Consiliency/jevdrill#111,
> Consiliency/jevdrill#132 and Consiliency/jevdrill#150, one round
> each.
> This is a reviewed plan. It verifies no criterion.

## Context

The October plan (tag `pr1-final-record`) was reviewed only by its planner and
is not accepted.

The JEV Drill side of HOST is largely on `main`. The host side lives in
`Consiliency/agent-harness`, where it is a draft (Consiliency/agent-harness#2071).
This plan was written against that draft. Execution apart from SL-1 and SL-5, lanes
that need only GitHub CI, waits for a commit that repository has
accepted. SL-0 checks R1 to R5 against it and records the install inputs of R6;
SL-3's first hosted run tests R6. Nothing here runs a collector, lands a held
file, requests a host run, spends money or closes a gate.

Length exception: this plan exceeds 3,000 words because every clause is mapped
to code, control, falsifier and evidence kind, and the cross-repository
conditions are stated in full.

## State of `main` at `998912b1e`

**On `main`.** The stack in [`plans/pr1-stack-split-20261119.md`](pr1-stack-split-20261119.md)
landed October's contracts, notices, evaluator and protocol, and the inherited
ROUTE verifier, not its probes.

**Held at the tag, not on `main`.** `scripts/verify_host_phase.py`,
`tests/verification/test_host_phase.py`, `.github/workflows/host.yml`, the seven
files of `tests/conformance/` (`conftest.py`, five test files, one fixture), the
probes `research/evaluation/host/test_bridge_probe.py` and
`test_baseline_probe.py`, `docs/host-interfaces.md`, `docs/host-readiness.md`,
and October's `evidence/HOST/**`. The October evidence is not restored: the
handoff record is regenerated (pin step); the expected-test lists are the LEARN
plan's (J4); the coverage and spec-delta records are re-made in SL-3; receipts,
verdicts and history are never committed.

**Exists nowhere.** An accepted host-integration commit; any CI run of its
tests; a HOST receipt from a hosted runner; a handoff record that names a
commit; JEV-side controls for recursion bypass, dry runs and mismatch advice;
any live evaluation; any record of a decline.

## External Inputs

- Host integration, inspected: draft Consiliency/agent-harness#2071, head
  `784d1595a08f42519862ae5f9336f20186d83c4b`, parent
  `56dce95a52625a58cd08911f8f623c637bf52e44`, package version 0.7.20. On
  2026-11-22 it was 1 commit ahead of and 1,495 behind that repository's
  `main` (package 0.7.39), conflicting, with no test run in that repository's
  CI. That `main` tests Linux only, on Python 3.12. This is an inspected draft,
  not an accepted revision.
- Supported interfaces used: `runner.discover_jevdrill_work_units`,
  `runner.launch_delegated_child`, `runner.launch_harness_lane_work_unit`;
  `launcher.build_launch_request`, `build_launch_spec`, `launch_with_spec`;
  `JevDrillAdapter`, `JevDrillTransport`, `JevDrillUnavailable`, `ReportQueue`;
  and the test names listed in R5.
- JEV Drill on Python 3.14 (`pyproject.toml:9`); BAML `baml-language-0.20.1` and
  `baml-bridge==0.20.1`, unchanged. The companion runs in its own environment on
  the Python its CI tests (J7).
- Read inputs: `main`, the tag and the draft above. No research corpus,
  holdout, credential, provider log or private repository.

## Interface Freeze Gates

- [ ] IF-0-HOST-1 — Installed discover → validated `DiscoveryResult` → harness
  decomposition → at least two `DiscoveryRouteInputs` tasks → independently
  validated `RoutingDecision` → existing launch constructors → `ExecutionRun`,
  report and durable acknowledgment, with one bounded queue and notice
  retrieval, on Linux, macOS and Windows in one workflow run.
- [ ] IF-0-VC-2 (plan-level, not a roadmap gate) — `scripts/verify_host_phase.py`
  rejects invalid, stale, skipped, constant-only or foreign receipts.

## Criteria, clause by clause

Key. "main" marks a test id that resolves on `main` today. "D" marks a
deliverable: the id exists at the tag unless marked "new". "HI" marks a test in
the host integration at the pinned commit, under `phase-loop-runtime/tests/`;
its source is cited relative to `phase-loop-runtime/src/phase_loop_runtime/`.
Evidence kinds: native CI run; synthetic; simulated; generated configuration;
needs the host integration; needs a container; needs an owner input. Nothing
below is verified.

**EC-HOST-1**

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Main, delegated and lane execution apply validated plans | `runner.py:3391,5570,6282`; decision `src/jevdrill/application.py:583`; `ExecutionRun` `baml_src/contracts.baml:78` | D `tests/conformance/test_launch_paths.py::test_real_main_delegated_lane_constructors`; HI `test_jevdrill_adapter.py::test_real_runner_construction_sites_reach_bridge` | An entry point missing, or a launch with no `applied_plan_id` | native CI run; needs the host integration |
| Report substitutions and observations | `substitution_reason` `contracts.baml:78`; `src/jevdrill/storage.py:2004` | main `tests/analysis/test_observations.py::test_substitution_preference_and_evaluation_are_distinct`; HI `test_jevdrill_adapter.py::test_observed_substitution_is_not_attributed_to_selected_plan` | A substitution attributed to the selected plan | native CI run; needs the host integration |
| Preserve permission restrictions | `jevdrill_adapter.py:517-538,873-881` | D `test_launch_paths.py::test_entered_permission_expansion_denials`; HI `test_jevdrill_adapter.py::test_forged_capability_or_candidate_cannot_expand_authority` | A widened launch that starts | native CI run; needs the host integration |
| Prevent recursive routing | `recursion_bypass` `contracts.baml:51`, honoured `application.py:821`; propagation in the host integration | No control on `main` (no test sets the flag): D new, SL-1; HI `test_jevdrill_adapter.py::test_dry_run_and_recursion_bypass_do_not_route` | A bypassed request that the host still routes or JEV still judges | native CI run; needs the host integration |
| Acceptance failures supply bounded rerouting context | `retry_context` `contracts.baml:51`; bound `application.py:619-620`; host half `jevdrill_adapter.py:499` | main `tests/application/test_route_integration.py::test_retry_requires_recorded_run_and_remaining_attempt_authority`. Host half: HI `test_jevdrill_host_gaps.py::test_acceptance_failure_builds_bounded_retry_context`, `::test_supplied_retry_context_cannot_widen_or_bypass`, `::test_unrecorded_supplied_context_never_launches` (1 case each), `test_host_integration_runner.py::test_acceptance_verdicts_reach_the_observer` (21 cases), three platforms | A retry accepted with no recorded failed run; a host retry lacking its context, naming another task's run, widening its budget, or unrecorded yet launched | native CI run; needs the host integration |
| Guidance not reinjected on retries | `jevdrill_adapter.py:578-579` | HI `test_jevdrill_adapter.py::test_guidance_is_verified_injected_once_and_deactivated` | An optional revision appended again when the prompt is reused | needs the host integration |
| Deactivates at task end, reporting host limitations | `guidance_deactivated` `contracts.baml:79`; reasons `host_integration.py:102` | Same HI test. Host limitations: HI `test_jevdrill_host_gaps.py::test_deactivation_reports_the_host_limitation` (5 cases, none timed-out or stalled), three platforms | No deactivation event at task end, or a reason other than that case's limitation | needs the host integration |
| Dry runs never become execution-success evidence: ordering | `dry_run` `contracts.baml:50`; excluded from ordering `application.py:898` | D new, SL-1; HI `test_dry_run_and_recursion_bypass_do_not_route` | A dry run that reaches learned-policy ordering | native CI run; needs the host integration |
| Dry runs never become execution-success evidence: counting | Counted on `main` (`storage.py:884-935`; Consiliency/jevdrill#109) | D new, SL-5 | A dry run counted, in the deciding store or after export and import | native CI run |

**EC-HOST-2**

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Hooks and explicit reporting use one durable bounded queue | `jevdrill_queue.py`; enqueued at `jevdrill_adapter.py:825-838`; hook `:763-801` | HI `test_jevdrill_queue.py::test_overflow_and_expiry_have_persistent_loss_counters`; D `tests/conformance/test_transport_queue.py::test_entered_ack_loss_and_cross_producer_deletion`. Explicit reports: D new, SL-7, through R5's hook, three platforms, relying on: one queue; a report the hook accepts is in it and counted; a report it does not accept is made known to its caller; enqueue order shared; delivery order unconstrained, later losses counted queue-wide (`docs/jevdrill-integration.md:165-168`); an unconfirmed enqueue may already be stored (`:160`) | A report dropped without a loss count; an explicit report the hook accepted that is not durably in the same queue, or that is lost without a loss count; or one it did not accept without its caller being told | needs the host integration |
| Redacted before persistence | Queue in the host integration; `_sanitize` refuses, never rewrites, `application.py:68`, applied `:1230` | main `tests/privacy/test_round41_learning.py::test_report_sensitive_map_key_rejects_before_persistence`, `tests/privacy/test_sink_proof.py::test_a_report_with_a_refused_identifier_is_refused_before_it_is_stored`; HI `test_jevdrill_adapter.py::test_production_sanitizer_rejects_raw_fields_and_erases_free_text`; D `tests/conformance/test_usage_reporting.py::test_installed_usage_persistence` (11 cases) | A sentinel in the queue file or the store | native CI run; needs the host integration |
| Idempotent acknowledgments and recovery | `storage.py:2004`; `contracts.baml:86-89` | main `tests/application/test_application.py::test_report_is_a_versioned_durable_acknowledgment`; HI `test_jevdrill_queue.py::test_acknowledgment_loss_replays_exact_report`, `::test_process_crash_windows_recover_durable_reports`, `::test_only_matching_durable_acknowledgment_removes_report` | A report removed on a non-durable acknowledgment | native CI run; needs the host integration |
| Disconnects and capability mismatches include supported resolution advice | `contracts.baml:54`; `src/jevdrill/routing.py:97-105`; disconnect advice `host_integration.py:140` | No control on `main`: D new, SL-1. Disconnect advice: HI `test_jevdrill_host_gaps.py::test_route_disconnect_carries_advice` (2 cases), `::test_report_disconnect_keeps_backoff_and_advises` (1 case), `test_host_integration.py::test_disconnect_advice_is_exact_per_operation` (1 case), three platforms | A mismatch without the supported refresh advice; a disconnect lacking its operation's advice | native CI run; needs the host integration |
| Host choices separate from check results | `contracts.baml:81-82` | main `test_observations.py::test_substitution_preference_and_evaluation_are_distinct` | A host choice counted as a check | native CI run |
| Unknown telemetry is not fabricated | `contracts.baml:4` | main `test_observations.py::test_missing_failed_canceled_corrected_and_unknown_observations`; HI `test_jevdrill_usage.py::test_incomplete_drain_is_unknown_and_bounded`, `test_jevdrill_discovery.py::test_native_unsupported_observer_records_unknown_capture`; D `test_installed_usage_persistence` | A missing counter reported as a number | native CI run; needs the host integration |
| Pending notices shown on the next connection | `application.py:1242`; `storage.py:2311`; `src/jevdrill/cli.py:87` | main `tests/storage/test_host_notices.py::test_notice_scope_reads_and_cross_producer_deletion`, `tests/application/test_host_notices.py::test_notice_snapshots_do_not_mutate_retry_or_replay`; D `tests/conformance/test_notices.py::test_every_report_connection_queries_notices`; D new, SL-2: a pending notice reaches the notice sink | A report connection with no notice query before it, or a notice that never reaches the sink | native CI run; needs the host integration |

**EC-HOST-3** (the reading is under "Readings and points settled")

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Linux, macOS and Windows contract suites pass | `scripts/verify_contract_phase.py:71` | main `tests/contracts/test_host_contracts.py::test_host_shared_contract` (28 cases), three platforms in the CONTRACT workflow; inherited ROUTE regressions in each HOST receipt | A row decided differently on one platform | native CI run |
| Independent implementation, review and documentation evaluations pass predefined correctness and privacy gates on development and validation splits | `src/jevdrill/evaluation.py:73`, `:102`; `research/evaluation/host/protocol.json` (`host-synthetic-v2`, six cases) | main `tests/evaluation/test_host_acceptance.py::test_independent_controlled_artifact_checks` (fixed programs, not routed); D `test_launch_paths.py::test_independent_checks_reject_entered_routed_artifacts` (routed) | A damaged routed artifact, privacy leak or swapped split that passes | synthetic; native CI run; needs the host integration |
| Untouched holdout reserved for PREPARE | Protocol `holdouts_opened: false` | main `test_frozen_groups_are_disjoint_and_holdouts_unopened` | A witness with a holdout opened | synthetic |
| Uncertainty and routing overhead against all applicable baselines | Protocol baselines (three applicable; `previous_policy`, `retrieval` not applicable with reasons); timings from the probes | D `test_independent_checks_reject_entered_routed_artifacts` (baselines; re-cut to require each case's timings). Uncertainty: recorded as `insufficient_evidence`; six synthetic cases support no interval | A missing applicable baseline, or a case without its measured overhead | synthetic |
| Insufficient evidence blocks performance claims | Protocol `performance_claims`; reducer witness check | main `test_frozen_groups_are_disjoint_and_holdouts_unopened`; D verifier fault `quality_claim` | Any other value passes | synthetic |
| A live development or validation evaluation | — | Outside the criterion as read below: none is authorized | — | needs an owner input |

**EC-HOST-4**

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Installed flow takes an objective through discovery and returns selected guidance | `application.py:107`; `cli.py:85`; `runner.py:260-277` | HI `test_jevdrill_discovery.py::test_installed_discovery_decomposition_two_task_launch` (2 cases), `::test_installed_discovery_status_gates_planning[no_optional_guidance]`; D `tests/conformance/test_discovery_handoff.py::test_installed_discovery_harness_planning_two_independent_tasks` | Entered trace lacks `main`, `open_application`, `discover`, `next_question` or `route`; or the planner refuses a no-guidance result | needs the host integration |
| The harness decomposes it | `runner.py:260-277` | HI `test_jevdrill_discovery.py::test_entered_discovery_requires_harness_decomposition`; same D | `planning.executor` absent or after the first route-v2 | needs the host integration |
| At least two tasks routed independently | `application.py:587-589` | main `tests/application/test_discovery_application.py::test_public_discovery_two_independent_tasks_and_replay` (synthetic caller); HI and D as above | One task, or equal model and effort | native CI run; needs the host integration |
| Objective, skill, task and decision links | `baml_src/discovery.baml:90-91`; `storage.py:1906` | main `test_discovery_application.py::test_bad_links_never_enter_prepare`; D `test_discovery_handoff.py::test_entered_reference_deletion_revision_and_policy_controls`; HI `test_jevdrill_discovery.py::test_entered_linked_launch_rejections` (5 cases) | A forged, deleted or stale reference that launches | needs the host integration |
| Guidance lifetime and substitutions | As EC-HOST-1 | HI `test_guidance_is_verified_injected_once_and_deactivated`; prompt isolation in the two-task test | Another objective's instructions in a task prompt | needs the host integration |
| The harness may retain its current model | `jevdrill_adapter.py:571-573`: an operator-set model refuses the route | HI `test_jevdrill_adapter.py::test_override_staleness_and_final_token_enforcement` shows that refusal. Launch keeping it: HI `test_jevdrill_host_gaps.py::test_operator_model_is_kept_through_launch` (1 case), three platforms | A route or launch spec replacing an operator-set model or effort | needs the host integration |
| Or decline a recommendation | In the host integration | HI `test_entered_linked_launch_rejections[decline]`; D `test_entered_reference_deletion_revision_and_policy_controls` | A decline that starts a run | needs the host integration |
| Production paths, no injected preselected guidance | As the first row | As the first row; reducer entered-path check | Selected guidance supplied without `discover` | needs the host integration |
| No recursive routing; no forced single model per skill | As EC-HOST-1; `application.py:583` per task | As EC-HOST-1; reducer requires a distinct decision per task, two models and two efforts | A reused decision, or identical configurations | needs the host integration |

**Scope notes and gates**

| Item | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| JD-084: leased macOS launch rejects before startup and names a Linux worker; Linux proves leased cleanup | `launcher.py:2981-2988`, `:2762` | HI `test_phase_loop_launcher.py::test_launcher_accepts_explicit_nonserialized_lease_authority` (on Linux: reaps the tree and frees the lease) and `::test_supervised_launch_drains_retained_stdout_before_returning` (on Linux: stdout drain only), required passed in the Darwin and the Linux receipt | A macOS executor that starts, a Linux receipt standing in for macOS, or a Linux tree or lease that outlives the launch | native CI run; needs the host integration |
| JD-083: estimated cost with no ceiling; ceilings need verified whole-run limits | `jevdrill_adapter.py:873-881`; JEV side `application.py:583` | main `test_route_integration.py::test_builtin_task_judgment_keeps_verified_spending_bounds`; HI `test_jevdrill_adapter.py::test_requested_ceiling_rejects_unproven_executor_limits`, `::test_override_staleness_and_final_token_enforcement`, `::test_no_requested_ceiling_does_not_require_token_enforcement` | A ceiling accepted without enforcement, or a route with no ceiling refused | native CI run; needs the host integration |
| IF-0-HOST-1 | The four criteria | D `test_installed_discovery_harness_planning_two_independent_tasks`; reducer `produced_if_gates` only when every clause of the four criteria is covered and its controls pass where they run, in three receipts of one run | A gate produced with a clause not covered, a criterion failing or a platform missing | native CI run, no model called; needs the host integration |
| IF-0-VC-2 | D `scripts/verify_host_phase.py` | D `tests/verification/test_host_phase.py::test_reducer_rejects_invalid_receipts` (19 cases at the tag, plus one per new rejection, each asserting its own error), `::test_missing_companion_configuration_is_failure`, D new `::test_reducer_accepts_valid_receipts` | A forged, skipped or foreign receipt passes, or a valid one is rejected | native CI run |
| Readiness rechecked before launch | `jevdrill_adapter.py:885-890` | HI `test_jevdrill_host_gaps.py::test_readiness_expiring_in_a_final_callback_refuses_launch`, `::test_readiness_expiring_during_the_started_write_refuses_launch` (1 case each), `::test_lock_wait_cannot_outlive_readiness` (2 cases), three platforms; unlinked launches only | A launch after readiness expired | needs the host integration |
| Budget passed after host spawn time | Reserve `jevdrill_adapter.py:53`, `:170-175`; child clock `src/jevdrill/cli.py:5`, `:112` | HI `test_jevdrill_host_gaps.py::test_budget_reserves_spawn_time`, `::test_over_reserve_spawn_is_bounded_by_the_parent_deadline` (1 case each, controlled clock), three platforms. Limit: a start outrunning the reserve tells the child it has more time than it has; the host's deadline ends the call; repeated flags pass. Basis, Linux only: 30 starts, CPython 3.14.4; cold 79.9 ms; warm median 72.4, p95 94.2, maximum 100.9 ms (`docs/jevdrill-integration.md:216-220`) | A budget passed without the 250 ms reserve, or a child outliving the host's deadline | needs the host integration |
| Ordinary macOS execution stays local | `launcher.py:2981-2988` refuses only leased Darwin launches | D new, SL-7; macOS only, required in the Darwin receipt; Linux does not stand in | An ordinary macOS launch refused, forwarded or not local | native CI run; needs the host integration |
| No silent forwarding | `jevdrill_adapter.py:487-496`; no check without `.jevdrill/harnesses.yaml` (`docs/jevdrill-integration.md:126`); routed launches execute locally (`launcher.py:2981-2988`) | HI `test_jevdrill_host_gaps.py::test_undeclared_identity_makes_no_cli_request` (3 cases), `::test_declared_identity_and_absent_file_still_route` (1 case), three platforms. Limit: a forward beside JD-084's refusal is unobserved | A CLI request for a pair a present declaration omits, or a declared pair refused | needs the host integration |

Other scope notes (`specs/phase-plans-v1.md:193`, `:195`): the last four rows.
At Consiliency/agent-harness `3a588dd19a52a28e4e5b2cd786e2799f381cdd15`, its own
run passed `test_jevdrill_host_gaps.py` on Linux, macOS and Windows, none
skipped; no workflow there runs `test_host_integration*.py` off Linux. R3
applies.

## Readings and points settled

- **EC-HOST-3.** Covered by the three-platform contract suites and the
  frozen synthetic protocol run through the routed path. Every performance claim
  is recorded as `insufficient_evidence` and the evaluation is labelled
  synthetic. A live evaluation is outside this reading. Whether that closes the
  criterion is the owner's decision at the gate, with the roadmap's rule on
  substitute or proxy evidence (`specs/phase-plans-v1.md:354`) before him.
- **Declining a recommendation.** Tested as: the harness declines and no
  routed run starts. Learning sees a host preference only as a choice among runs
  that happened (`storage.py:1014-1018`), so a decline with no run leaves
  nothing to misclassify; that is a stated limit.
- **`tests/conformance/test_usage_reporting.py`: run.** The verifier selects it
  on all three platforms, 11 cases each, as a control of EC-HOST-2. Reason: it
  is the only test that drives installed usage reporting through the companion
  queue for missing, unsupported and lagged telemetry with privacy sentinels.
  No verifier has run it; if it cannot run on a platform, SL-2 says so and the
  control is declared for the platforms it runs on. It is never skipped.
- **Judgment policy in the installed flow: `JudgeCandidate-v2` through the
  loopback mock.** At least one task of the installed two-task flow carries a
  route judgment policy at `JudgeCandidate-v2`, answered by the loopback mock
  (`MockObserveCandidate`, `baml_src/jev.baml:29`), which the fixture's wrapper
  puts in place of the provider function, as the draft's does for discovery; no
  judgment request leaves the runner. Reason: JEV Drill dispatches
  only v2 (`src/jevdrill/integrations/jev.py:25`; refusal
  `application.py:825-828`), and a flow with no policy, as at the draft, cannot
  catch a companion that rejects v2. If the accepted commit's fixture cannot
  carry such a task without a change in that repository, the pin step records
  it, declared change 14 is dropped and no control sends a judged route through
  the host integration; no condition is added.
- **JD-084's controls** are the two module-level launcher tests named above. At
  the draft they carry no `dotfiles_integration` marker and skip unless
  `PHASE_LOOP_TDD_EXPECT_SCHED=1`, which the collector sets. A commit that marks
  them leaves JD-084 not covered.
- **What the deselection does not exercise (J6).** The 53 tests of the marked
  class in `test_phase_loop_launcher.py`: launcher skill and adoption bundle
  building and the execute path that resolves a dotfiles skill source and
  profile overlay. HOST's evidence says nothing about them. Each launch-path
  claim of EC-HOST-1 rests on a selected test; SL-3's coverage record shows the
  mapping.

## Cross-Repo Gate

This plan owns no path in `Consiliency/agent-harness` (`specs/phase-plans-v1.md:192`).
jevdrill does not review the host integration; it pins a commit that repository
has accepted. The conditions of the pin:

- **R1 — One accepted commit** on that repository's `main`, merged under its own
  rules with its required checks passing, named by its full 40-character SHA.
  Under `phase-loop-runtime/`: `jevdrill_adapter.py`, `jevdrill_queue.py`,
  `runner.py`, `launcher.py`, `observability.py`; the twelve test files
  (`test_jevdrill_adapter.py`, `_queue`, `_discovery`, `_input`, `_usage`,
  `_diagnostics`, `test_phase_loop_launcher.py`,
  `test_phase_loop_work_unit_observability.py`, `test_windows_locking.py`,
  `test_launcher_liveness.py`, `test_windows_processes.py`,
  `test_windows_storage.py`) and every helper they import;
  `test_jevdrill_host_gaps.py`, helper `jevdrill_fixture_values.py`;
  `test_host_integration*.py`;
  `tests/fixtures/jevdrill/` with 14 schemas, 3 fixtures and `digests.json`; a
  `pyproject.toml` and `uv.lock` whose locked sync imports `phase_loop_runtime`
  from the checkout's `src`. Nothing need match October's digests or 0.7.20.
- **R2 — Contract copies are jevdrill's.** Each schema copy is byte-identical to
  its namesake in `schemas/` at a jevdrill `main` commit at or after
  `998912b1e`, named by the pull request. Each fixture equals its namesake in
  `tests/contracts/fixtures/` once `<jev-token-counter-revision>` is replaced by
  `utf8-bytes-upper-bound-v1`. `digests.json` agrees.
- **R3 — Tested there.** The twelve files pass in that repository's own GitHub
  Actions on Linux at that commit. Asked for, each with a fallback: the tests
  needing an installed JEV Drill run there against the R2 commit, JEV Drill on Python 3.14 and the tests on R6's Python;
  the twelve files run on hosted macOS and Windows. Where either is not done,
  jevdrill's `host.yml` run is the first; a companion failure there is reported
  to that repository and HOST waits for a new accepted commit.
- **R4 — No private dependency.** No selected test needs `Consiliency/dotfiles`,
  another private repository or a secret. jevdrill deselects exactly
  `dotfiles_integration` and tolerates no other skip; none of the 37
  companion controls and none of the four LEARN files carries that marker.
- **R5 — Names kept, or the change declared:** `launcher`, `runner`, `models`,
  `jevdrill_adapter.JevDrillTransport`, `JevDrillUnavailable`,
  `jevdrill_queue.ReportQueue`; `test_jevdrill_discovery.installed_discovery`,
  `.linked_task`, `.test_installed_discovery_decomposition_two_task_launch`;
  `test_jevdrill_adapter.FIXTURES`, `.adapter_fixture`;
  `test_jevdrill_usage.records`, `.synthetic_spec`, `.values`;
  `phase_loop_test_utils.make_repo`, `.write_phase_plan`; hook
  (`docs/jevdrill-integration.md:148-189`):
  `JevDrillAdapter.active_execution_run_ids`, `.run_event_identity`,
  `.enqueue_run_event`, `.run_report_counts`, `.queue.status`,
  `LaunchResult.jevdrill_execution_run["execution_run_id"]`.
- **R6 — Installs on hosted runners.** The pull request states the sync command
  and the Python its CI tests (3.12 today), and the command works on hosted
  Linux, macOS and Windows.

**jevdrill's own obligations.**

- **J1.** `host.yml` takes `companion_ref` as a full SHA, no default, and before
  it checks that repository out requires it to equal the handoff record's
  commit; checks out that one public repository with the read-only token; every
  checkout sets `persist-credentials: false`; `permissions: contents: read`; no
  cache, no secret, no dotfiles checkout. (`learn.yml` is the LEARN plan's.)
- **J2.** A receipt records the repository, the commit and a clean checkout; the
  reducer rejects a commit that is not the handoff's.
- **J3.** The handoff record is regenerated from the accepted commit and names
  the repository and commit, not a path.
- **J4.** The expected-test lists are read only by the LEARN verifier; rebuilding
  them by a CI run is the LEARN plan's, with `learn.yml`.
- **J5.** The collector compares the companion's contract copies with
  jevdrill's `schemas/` and fixtures at the commit under test, with the one
  substitution. This settles Consiliency/jevdrill#82.
- **J6.** The companion command carries `-m "not dotfiles_integration"` as a
  named constant bound in the command digest.
- **J7.** The companion's Python version is set explicitly and recorded in the
  receipt.

**The pin step** (SL-0) comes before every lane that needs the host
integration. Its writer regenerates the handoff record from the accepted commit.
The record holds only what anyone can recompute from that public commit; the
pull request's correctness seat recomputes it, and every collection checks it
against the checkout. If the commit breaks an item of R5, this plan gets one
amendment of one round.

**Where the evidence comes from.** One dispatched `host.yml` run on GitHub's
hosted Linux, macOS and Windows runners, JEV Drill on Python 3.14. Only if
hosted runners prove unable to run the host integration
would a host run be requested, then and not now: one collection per machine on
one Linux, one macOS and one Windows machine; both commits as full SHAs with
clean checkouts; no root, no sudoers entry, no docker; the verifier's two
bounds; a receipt carrying both commits, the UTC start time and a nonce issued
with the request, and no hostname or local path; nothing committed. This is a
possibility, not a request.

## Lane Index & Dependencies

- SL-0 — Pin step; Depends on: an accepted commit; Blocks: SL-2, SL-3, SL-4, SL-7, SL-8; Parallel-safe: no
- SL-1 — JEV-side controls; Depends on: (none); Blocks: SL-3; Parallel-safe: no
- SL-2 — Conformance and probes; Depends on: SL-0; Blocks: SL-3; Parallel-safe: no
- SL-3 — Verifier and workflow; Depends on: SL-0, SL-1, SL-2, SL-5; Blocks: SL-4; Parallel-safe: no
- SL-4 — Readiness docs; Depends on: SL-8 and a run after it; Blocks: (none); Parallel-safe: no
- SL-5 — Dry-run evidence fix; Depends on: (none); Blocks: SL-3; Parallel-safe: no
- SL-6 — Collection bound; Depends on: SL-3; Blocks: the next dispatch; Parallel-safe: no
- SL-7 — Conformance for items 3 and 8; Depends on: SL-0; Blocks: SL-8; Parallel-safe: no
- SL-8 — Verifier and coverage; Depends on: SL-0, SL-7; Blocks: the next dispatch; Parallel-safe: no

## Lanes

### SL-0 — Pin step

- **Needs:** an accepted host-integration commit.
- **Owned files:** `evidence/HOST/adapter-handoff.json` (repository, commit,
  package version and module digests; no path).
- **Delivers:** J3; R1 to R5 checked against the commit and stated in the pull
  request, which names the jevdrill commit of R2 and any HI control of the
  clause tables that the commit lacks or marks: its clause becomes not covered.
  It needs no workflow run. R6 is shown by the first `host.yml` run (SL-3); if
  that run shows it false, HOST waits for a new accepted commit.

### SL-1 — JEV-side controls

- **Needs:** GitHub CI alone. It needs no accepted commit and may be
  executed before the pin step.
- **Owned files:** `tests/application/test_host_routing.py` (new).
- **Delivers:** controls, entered through `Application.route`, for: recursion
  bypass makes no judgment call; a dry run is never ordered; a
  capability mismatch carries the supported advice. Run by `unit.yml`
  on three platforms without an edit to it; SL-3 makes them HOST controls.

### SL-2 — Conformance and probes

- **Needs:** an accepted commit; GitHub CI.
- **Owned files:** `tests/conformance/**`,
  `research/evaluation/host/test_bridge_probe.py`, `test_baseline_probe.py`.
- **Delivers:** the held files adapted to the pinned commit; the v2
  judgment-policy task, subject to its fallback; the notice-sink test; baseline
  timings required. Nothing runs these files until SL-3: the conformance fixture
  loads its verifier. `tests/conformance` does not join `testpaths`;
  `pyproject.toml` is unchanged.

### SL-3 — Verifier and workflow

- **Needs:** an accepted commit; GitHub CI.
- **Owned files:** `scripts/verify_host_phase.py`,
  `tests/verification/test_host_phase.py`, `.github/workflows/host.yml`,
  `.gitignore`, `tests/verification/test_route_phase.py`,
  `evidence/HOST/coverage.json`, `evidence/HOST/spec-delta.json`.
- **Delivers:** the held verifier, its tests and workflow with every declared
  change below; fix lane for Consiliency/jevdrill#71, #73, #74 and #82. Its
  reducer tests pass in CI. Once the lane is on `main`, its writer dispatches
  `host.yml` with the pinned SHA and records the run.

### SL-4 — Readiness docs

- **Needs:** the result of the run after SL-6, with its verdict artifact if
  there is one.
- **Owned files:** `docs/host-interfaces.md`, `docs/host-readiness.md`, and the
  first block of `docs/roadmap-status.md`.
- **Delivers:** the held docs rewritten: the queue as the accepted commit
  implements it; the verdict as the run's artifact, as in
  `docs/route-readiness.md`; the companion's environment for the accepted
  version; the run linked, with its verdict or why it has none; no October receipt,
  no history, no LEARN instruction.

### SL-5 — Dry-run evidence fix

- **Needs:** GitHub CI alone. Not cut together with LEARN's or PREPARE's SL-1.
- **Owned files:** `src/jevdrill/storage.py`, `application.py` and
  `routing.py`, only where a decision's mode is recorded or read;
  `tests/storage/test_dry_run_evidence.py` (new); any storage migration.
- **Delivers:** without a public contract change, no dry run becomes an
  observation in either store the counting row names. Control:
  Consiliency/jevdrill#109's reproduction, for every report kind and
  `event_type`, and none, in that store and a fresh one after import. A changed response stays
  within the public contract, declared under CONTRACT's rules. If the received store needs a public contract change,
  that half is "not covered: needs an owner input"; the deciding store is
  still fixed.

### SL-6 — Collection bound

- **Needs:** GitHub CI.
- **Owned files:** `scripts/verify_host_phase.py`,
  `tests/verification/test_host_phase.py`; `.github/workflows/host.yml`, its job
  timeout only; `tests/verification/test_route_phase.py`, its downstream-command
  test only.
- **Delivers:** declared change 17. HOST's part is all of a collection outside
  the unmodified ROUTE collector call, timed by the collection's own clock. Its
  control fails if the inherited command differs from ROUTE's own; a part over
  its bound, or a receipt lacking part times, is accepted; a moved control is
  missing from the receipt, or a failed one from its failure summary; a
  control's id or count stops being required, or is counted from two sources; or
  the inherited budget differs from ROUTE's.

### SL-7 — Conformance for items 3 and 8

- **Owned files:** new files under `tests/conformance/`; any needed probe
  under `research/evaluation/host/`.
- **Delivers:** the item 3 and 8 controls.

### SL-8 — Verifier and coverage

- **Owned files:** `scripts/verify_host_phase.py`,
  `tests/verification/test_host_phase.py`, `evidence/HOST/coverage.json`.
- **Delivers:** the nine clauses covered with their controls;
  `test_jevdrill_host_gaps.py` and `test_host_integration*.py` in the companion
  command where they run; every new id and count bound; totals re-taken by
  collection. Its control fails on a clause covered with no control bound, a
  replaced id, an inexact count, or a gate produced with one not covered.

## Verification

Runs on `main` today:

```sh
uv run python -m pytest -q tests/storage/test_host_notices.py::test_notice_scope_reads_and_cross_producer_deletion tests/evaluation/test_host_acceptance.py::test_frozen_groups_are_disjoint_and_holdouts_unopened
```

Deliverables (the two verifier commands are steps of `host.yml`):

```sh
uv run python -m pytest -q tests/application/test_host_routing.py
uv run python -m pytest -q tests/storage/test_dry_run_evidence.py
uv run python -m pytest -q tests/verification/test_host_phase.py
uv run python scripts/verify_host_phase.py --local-only --agent-harness .host/companion
uv run python scripts/verify_host_phase.py --reduce-only --agent-harness .host/companion
gh workflow run host.yml --repo Consiliency/jevdrill --ref main -f companion_ref=<40-hex commit SHA>
```

The companion command, from the companion checkout, with
`PHASE_LOOP_TDD_EXPECT_SCHED=1` (deliverable; on macOS and Windows the
`_input`, `_usage` and `_diagnostics` files are left out, as at the tag):

```sh
<companion python> -m pytest -q -m "not dotfiles_integration" phase-loop-runtime/tests/test_jevdrill_adapter.py phase-loop-runtime/tests/test_jevdrill_queue.py phase-loop-runtime/tests/test_phase_loop_launcher.py phase-loop-runtime/tests/test_phase_loop_work_unit_observability.py phase-loop-runtime/tests/test_jevdrill_input.py phase-loop-runtime/tests/test_jevdrill_usage.py phase-loop-runtime/tests/test_jevdrill_diagnostics.py --junitxml=<temporary>/companion.xml --basetemp=<temporary>/companion-tests
```

`tests/test_jevdrill_discovery.py` runs separately, from `phase-loop-runtime`,
inside the conformance fixture, with the same deselection.

Effective `automation.suite_command`: `uv run python scripts/verify_host_phase.py --agent-harness .host/companion` (deliverable; a missing companion fails closed).

## The verifier

**It must check:** every control the clause tables name, by id and exact
count, on each platform where it runs; three native receipts from the same
workflow run; the companion at the pinned commit with a clean checkout; no
selected companion test failed or skipped; the deselection and substitution
constants bound in the command digest; the companion's contract copies equal to
jevdrill's; two or more tasks, each with its own decision; the coverage and
spec-delta records; two bounds, each part's time recorded: the inherited
regressions within ROUTE's own 600 seconds
(`scripts/verify_route_phase.py:556`), the rest within 900 seconds; a
collection over five minutes flagged (`specs/phase-plans-v1.md:354`); a
malformed receipt reported, not raised. A clause of the four criteria that is
not covered is reported so, never as passed, and no gate is produced while one
stands.

**It reads** the jevdrill checkout and the companion checkout at the pinned
commit.
**It writes** `evidence/HOST/platforms/`, `evaluation.json`, `history/` and
`verification.json`, all ignored by git. A verdict is the CI artifact of the run
that made it and is never committed.

**Declared changes to the held instrument:**

1. Reduce job gets "Require successful native jobs" as in `route.yml`; ignore
   rules for every path it writes; verdict uploaded only when the reduction ran
   (Consiliency/jevdrill#74).
2. `assertions_from` keeps class names in rebuilt ids, as the ROUTE verifier does, so that a rebuilt id names the test that ran.
3. A malformed `platforms/*.json` is reported, not raised: a verdict with an error, not a traceback.
4. Receipts name repository, commit and a clean checkout; the reducer rejects a
   foreign commit (J2).
5. `test_route_phase.py`: `host` returns to
   `test_native_download_excludes_prior_reduction_reports` and joins
   `test_reduction_runs_only_after_every_native_job_succeeded`;
   `test_downstream_commands_cover_phase_controls_and_bind_extra_paths` is
   restored. These tests of the workflows were cut down while `host.yml` was not on `main`.
6. `host.yml` as J1, with pinned actions and `workflow_dispatch`.
7. Contract-copy comparison against jevdrill's files replaces the raw handoff
   digest check (J5).
8. The deselection constant (J6); the companion Python recorded (J7).
9. Exact counts; a changed count is a declared change
   (Consiliency/jevdrill#71).
10. Same-run receipts only; any other is a diagnostic, never uploaded
    (Consiliency/jevdrill#73).
11. The handoff names repository and commit (J3).
12. `test_usage_reporting.py`, `test_host_routing.py`, `test_dry_run_evidence.py`
    and every "main" control of the clause tables become required controls, in the test paths and digest.
13. Every HI control of the clause tables added to the companion controls, on
    each platform where its file runs, the two JD-084 launcher tests among them.
14. The witness requires a v2 judgment-policy task.
15. The witness requires a distinct decision per task.
16. A clause not covered blocks the gate; the reducer's tests accept a valid
    receipt.
17. HOST's controls leave the inherited command, now `route.yml`'s, for a
    digest-bound command of the HOST collector's own; a receipt lacking a part's
    time, or a part over its bound, is rejected (SL-6).

Changes 12, 13, 15 and 16 bind the verdict to the rows' controls; 14 is
explained under "Readings and points settled".

The spec-delta check keeps `roadmap_amendment`: the roadmap sets it for JD-083
and JD-084 (`specs/phase-plans-v1.md:216`).

## Acceptance Criteria

- [ ] EC-HOST-1, EC-HOST-2, EC-HOST-3, EC-HOST-4 — by the controls and
  falsifiers of the clause tables, reduced by SL-3 from one run.
- [ ] IF-0-VC-2 — by `tests/verification/test_host_phase.py`.

## This plan may not claim

- Any criterion verified or any gate produced.
- Anything on the strength of the October reports, receipts or plans.
- That hosted runners can run the host integration.
- That the host integration is accepted, or works against `main`.
- Performance, quality, cost or savings.
- That a synthetic evaluation is empirical evidence. Synthetic HOST receipts are
  software conformance only; they supply no quality floor, guidance
  effectiveness or promotion evidence.
- That a decline is visible to learning.
- That the deselected launcher tests' behaviour is exercised.
- That Linux evidence proves JD-084 on macOS.
- That usage capture is exercised outside Linux.
- That dry runs decided without SL-5's fix are excluded.
- That an import detects a bundle that misstates a decision's mode.
- Ratified review, publication, adoption or release readiness.

## Attached backlog

| Item | Disposition |
| --- | --- |
| Consiliency/jevdrill#71 (exact counts) | Fix lane, SL-3 |
| Consiliency/jevdrill#73 (local receipts) | Fix lane, SL-3: same-run receipts only |
| Consiliency/jevdrill#74, for `host.yml` | Fix lane, SL-3 |
| Consiliency/jevdrill#82 (handoff against `schemas/`) | Fix lane, SL-0 and SL-3 (J3, J5) |
| R1 to R6 and J1 to J7 | R: pin conditions, SL-0. J: fix lanes SL-0 and SL-3; J4 is the LEARN plan's |
| The changes ruled for this cut earlier (declared changes 1 to 6 and 11) and the conformance landing rules | Fix lanes, SL-0, SL-2 and SL-3 |
| HOST coverage and spec-delta records | Re-made, SL-3 |
| Consiliency/jevdrill#109 (dry-run counting) | Fix lane, SL-5 |
| Conditional host run | Owner input, only if hosted runners fail |
| ROUTE verifier not reopened; the deadline-failure rule | Stated limits, standing |
| `host.yml` run 45236348900 | Fix lane, SL-6 |
| Consiliency/jevdrill#120 | SL-7, SL-8 |

## Owner inputs

- **Who takes the host integration to a merged state** in
  `Consiliency/agent-harness`. Without it, only SL-1 and SL-5 can be executed.
- **Closing the HOST gate**, including whether synthetic evidence with
  `insufficient_evidence` closes EC-HOST-3, and what to do about each clause left
  not covered: each blocks the verifier's gate.
- **A live evaluation**, if wanted: an authority naming budget, models and
  expiry; added by amendment. Without it, EC-HOST-3 rests on synthetic evidence.
- **Making a decline visible to learning**: a contract change. Without it, the
  limit stands.
- **A host run**, only if hosted runners prove unable.

## Execution Notes

Execute serially, one writer per lane; each lane's scope is fixed before it is
cut, and it is reviewed as this plan was. No edit to `specs/phase-plans-v1.md`, `plans/manifest.json`
or `scripts/verify_route_phase.py`, except a defect in the ROUTE verifier that
the HOST verifier's use exposes. A failure caused by the product's deadline
follows the standing rule. Product calls keep their five-second deadline. A
local or diagnostic receipt never enters a verdict.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`; decision: `roadmap_amendment` (JD-083 and JD-084)
- target surfaces: shared event/adapter contracts and platform execution boundaries
- evidence paths: `evidence/HOST/spec-delta.json`, `evidence/HOST/verification.json`
- redaction_posture: `metadata_only`; missing/malformed evidence: `blocker_class=contract_bug`, non-human repair
- downstream handling: `replan_LEARN`, which the reducer checks; LEARN consumes IF-0-HOST-1 as defined here

`evidence/HOST/verification.json` is written inside the run and kept as its
artifact, not committed. No roadmap text is amended by this plan.
