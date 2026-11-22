---
phase_loop_plan_version: 1
phase: EXPERIMENT
roadmap: specs/phase-plans-v1.md
roadmap_sha256: 4ecbf27188b634d6ea5346cd67d61ab36d50d3ad0416a9a6d0d2602bb2698ab8
---

# EXPERIMENT: Comparisons and governed policy updates

> Review status: draft written by Claude Opus 5.5. Board: a Fable 5.2 president
> with three seats (correctness; security and privacy; alternate vendor).
> Rounds: to be filled in. Pull request: Consiliency/jevdrill#98. This is a
> reviewed plan. It verifies no criterion.

## Context

This plan revises EXPERIMENT against the amended roadmap, EC-EXPERIMENT-1 to 4
and IF-0-EXPERIMENT-1. It starts from the October plan held at the tag
`pr1-final-record`, without its local paths, recovery source, owner grants,
study preparation and image. That plan was reviewed only by its planner and is
not accepted as the required revision.

Nothing here runs a collector, lands a held file, requests a host run, calls a provider, reads a credential, spends money, proposes or authorizes a study, opens a holdout, promotes a policy or closes a gate.

The plan proposes no study. Each row is labelled by part: **1**, software on
GitHub CI; **2**, the restricted-runtime proof, which needs a container;
**3**, the development evaluation of EC-EXPERIMENT-4, which needs owner inputs.

Length exception: every clause is mapped to code, control, falsifier and
evidence kind.

## State of `main` at `e1e9dc339`

**On `main`, by stack pull request.** The roadmap's two lanes have landed.

| What | Pull request |
| --- | --- |
| Experiment, policy and calibration contracts and schemas | Consiliency/jevdrill#12 |
| Experiment and policy storage, `evaluation.py` and its tests | Consiliency/jevdrill#18 |
| `experiments.py`, policy code in `analysis.py`, `integrations/experiments.py` and `development.py`; first tests | Consiliency/jevdrill#44 |
| The four experiment and policy commands; further tests | Consiliency/jevdrill#54 |
| The calibration scripts, the discovery protocol, `experiment.yml`, `docs/evaluation-protocol.md` | Consiliency/jevdrill#76 |
| `docs/experiment-interfaces.md` | Consiliency/jevdrill#85 |

**Held at the tag, not on `main`.** `scripts/verify_experiment_phase.py`,
`scripts/verify_development_runtime.py`, their tests under
`tests/verification/`, `docs/experiment-readiness.md` and October's
`evidence/EXPERIMENT/**`. No evidence is restored: coverage and spec-delta
records are re-made (SL-4); receipts, verdicts and history are never committed.

**Exists nowhere.** A run of the restricted container on `main`'s code; a run
of `tests/promotion/runtime_recorded_evidence.py`, which no workflow, script
or test names and pytest does not collect by its file name; a comparison path in the host
integration; the "D new" controls; a completed study record.

**History, once.** On 2026-09-29 the owner made an exception for a development calibration pilot (`specs/jevdrill-design-input.md:588`). The roadmap's JD-078 note (`specs/phase-plans-v1.md:277`) names that pilot's caps: they are the record of the pilot, which is over, and not a limit for or a grant of anything here. On 2026-10-09 the owner approved one study authority of at most 28.20 USD; it expired on 2026-10-15, and its one run stopped incomplete (`docs/evaluation-protocol.md:21`). The October records name the image `sha256:70af8b01bcbd3a008522f36ea07b679f14f9ad3fb721868cf0cc3f80b7e3f958` (`scripts/verify_discovery_calibration.py:417`), a local id with no registry reference. None of this carries forward.

## External Inputs

- Host integration, inspected: as in the HOST plan (draft
  Consiliency/agent-harness#2071 at `784d1595a08f42519862ae5f9336f20186d83c4b`,
  unchanged on 2026-11-22). Its JEV Drill modules and tests have no
  experiment or comparison path.
- JEV Drill on Python 3.14 (`pyproject.toml:9`); BAML `baml-language-0.20.1`
  and `baml-bridge==0.20.1`.
- **Container image, inspected, not run:**
  `docker.io/library/node:24-bookworm-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54`
  (index digest), from registry metadata on 2026-11-22; its contents are
  unchecked. It must
  hold, for `src/jevdrill/integrations/experiments.py`: a POSIX `sh` with
  arithmetic, the entrypoint (`:78`, `:88`); `date +%s` (`:88`); a `timeout`
  taking `--foreground` and `-s KILL` (`:89`, `:100`); Node.js running `-e`
  with `--max-old-space-size` and loading `node:fs` (`:15`, `:89`); all as user
  `65534:65534` on a read-only root without network (`:66-74`). The product
  never pulls (`:63`) and takes only a local `sha256:` image id (`:26`).
- Read inputs: `main`, the tag and the draft above; no private corpus,
  holdout, credential, provider log or user database.

## Interface Freeze Gates

- [ ] IF-0-EXPERIMENT-1 — Authorized comparisons and objective-scoped
  promotion/rollback (`specs/phase-plans-v1.md:81`).
- Consumed: IF-0-LEARN-1, as the LEARN plan defines it.

## Criteria, clause by clause

Key, naming and evidence kinds as in the LEARN plan; column P is the part.
"main" controls run today in `unit.yml`, those under `tests/evaluation` and
`tests/contracts` in `contracts.yml`; both on Linux, macOS and Windows. Sources
are under `src/jevdrill/` unless a path says otherwise. Nothing below is
verified.

**EC-EXPERIMENT-1** (`specs/phase-plans-v1.md:269`)

| P | Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Deduplicated proposals | `storage.py:502`, `:530` | main `tests/application/test_experiments.py::test_queue_survives_restart_deduplicates_and_counts_distinct_tasks` | An equal proposal stored twice, or a second task uncounted | native CI run |
| 1 | Prioritize recurring uncertainty and expected benefit | `experiments.py:417-430` | main the queue test, `::test_queue_priority_and_scope_isolation`, `tests/storage/test_experiments.py::test_opted_out_equivalent_recurrence_cannot_increase_priority`; D new, SL-2: order follows each of recurrence, uncertainty and benefit varied alone | An order ignoring one of the three, or counting an opted-out task | native CI run |
| 1 | Only after explicit experiment enablement | Off by default, `settings.py:26`; `experiments.py:81-85` | main `tests/storage/test_experiments.py::test_resolved_settings_disable_even_an_enabled_grant`, `::test_settings_opt_out_after_admission_prevents_dispatch` | Admission or a start with experiments off | native CI run |
| 1 | And applicable standing authorization | `experiments.py:77-117`; none in the command line's application, `application.py:1384-1386` | main `tests/experiments/test_execution.py::test_authority_denials_never_dispatch_or_reserve` [8], `::test_default_has_no_authority_or_runner`, `tests/storage/test_experiments.py::test_all_grant_scope_fields_bind_admission` [4] | A reservation or start without a current, in-scope authority | native CI run |
| 1 | Default limits allow one background experiment/two candidates | No default, as decided (under "Readings"): both counts are required (`baml_src/contracts.baml:99`), at least two and one (`baml_src/boundary.json:137-142`) | D new, SL-2: this table's last row | A count supplied for a proposal that stated none | native CI run |
| 1 | With explicit compute/time | Required, `baml_src/contracts.baml:99`; within the authority, `experiments.py:108-116`, and the host, `:152-158` | main `test_execution.py::test_current_host_readiness_required` [11]; D new, SL-2: a limit above the authority's | A run admitted beyond the host's resources or its authority | native CI run |
| 1 | External per-experiment/daily caps | `experiments.py:48-52`, `:159-165`, `:231-240`; `storage.py:383-391` | main the readiness test, `test_execution.py::test_spend_reservations_survive_deletion_and_daily_rollover`; D new, SL-2: the daily cap alone, on its day and the next | A reservation above either cap | native CI run |
| 1 | Default counts do not enable experiments | `experiments.py:410-413`, `:432`; `contracts.py:189-198` | main `tests/application/test_experiments.py::test_proposal_cannot_self_authorize` [3], `tests/cli/test_experiments.py::test_real_cli_lists_experiments_without_enabling_execution` | A proposal carrying authority, or `execution_authorized` true | native CI run |
| 1 | Missing limits block execution | Counts and compute/time refused at parsing, `contracts.py:292`; a missing cap at admission, `experiments.py:48-50` | D new, SL-2: a proposal lacking each count or compute/time limit refused, nothing stored; admission lacking either cap refused before reserving | A proposal stored, or a reservation made, with a limit missing | native CI run |

**EC-EXPERIMENT-2** (`specs/phase-plans-v1.md:270`)

| P | Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Immediate host-accepted path | JEV side `integrations/development.py:580-584`, `:831` | main `tests/experiments/test_development.py::test_actual_immediate_host_acceptance_is_bounded_and_not_redispatched`. Host side: not covered; the draft has no "agent-harness comparison adapter/tests" (`specs/phase-plans-v1.md:286`) | A second dispatch, or completion without verified cleanup | simulated; native CI run; needs the host integration |
| 1 | Deferred/internal paths respect deadlines | `experiments.py:205-206`, `:291-292`; `integrations/development.py:1025-1035` | main `test_execution.py::test_recheck_before_dispatch_cancels_safely` [5], `test_development.py::test_development_worker_rechecks_frozen_inputs_and_authority` [5] | A start or request after the deadline or a clock regression | simulated; native CI run |
| 1 | Respect isolation | `experiments.py:134-151` | main the readiness test (isolation, capability) | A start with other isolation or a missing capability | native CI run |
| 1 | Respect contention | None | Not covered: no experiment code receives JD-074's contention report (`specs/jevdrill-design-input.md:562`); admission counts active runs only (`storage.py:376-382`) | — | — |
| 1, 2 | Internal code runs require restricted containers | `experiments.py:146-147`; `integrations/experiments.py:59-80` | D new, SL-2: internal readiness lacking only `restricted_container`, or only `network_disabled`, refused; part 2 | An internal start without either | native CI run; needs a container |
| 1, 2 | Absent runtimes disable code experiments | `integrations/experiments.py:53-54`; `integrations/development.py:482-483`, `:733-753` | main `tests/experiments/test_development_grader.py::test_native_macos_or_windows_requires_linux_grading_worker`; D new, SL-2: `DevelopmentRunner.prepare` refused without a container runtime; part 2 | A code experiment readied or graded with no Linux container runtime | simulated; native CI run; needs a container |
| 1 | Observed work retains host isolation | In the host integration | Not covered: no test | — | needs the host integration |
| 1 | Linux/macOS/Windows pause/cancel/unavailability tests preserve honest partial and missing-context evidence | `experiments.py:282-338`; `integrations/development.py:875-919` | main `test_development.py::test_resolved_pause_during_actual_call_prevents_later_call_and_retains_reservation`, `::test_development_cancel_inflight_waits_and_prevents_second_call`, `::test_development_missing_usage_stays_unknown`, `test_execution.py::test_cancellation_waits_for_cleanup_even_after_restart`, `::test_absent_host_after_dispatch_checkpoint_is_canceled_without_retry`, `::test_deletion_during_start_cannot_restore_content_or_accept_late_result` | A request after pause or cancel; `canceled` before cleanup; a late result kept after deletion; missing usage valued | simulated; native CI run |
| 1 | Shadow runs never duplicate external side effects | A required capability name only, `experiments.py:40` | Not covered: no test exercises a side effect | — | — |

**EC-EXPERIMENT-3** (`specs/phase-plans-v1.md:271`)

| P | Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Host preference remains separate from checks | `experiments.py:358-359`, `:383` | main `test_execution.py::test_completed_receipt_keeps_preference_separate_and_checks_binding` | A preferred plan's failed check stored as passed | native CI run |
| 1 | Measurements support reclassification | `analysis.py:254-330` | main `tests/promotion/test_recorded_evidence.py::test_recorded_evaluator_binds_real_durable_comparisons_without_new_calls` | A new request, or a lost measurement, on evaluation | simulated; native CI run |
| 1 | Policy changes require separate authority | `analysis.py:395-415`, `:571-581` | main `tests/promotion/test_lifecycle.py::test_grant_required_and_bounded_routes_survive_restart`, `::test_promotion_authority_cannot_cross_declared_scope` [2] | A policy activated without a current, in-scope authority | native CI run |
| 1, 3 | Blinded evaluation on policy-held-out/regression cases | `evaluation.py:316-319`, `:323-324` | main `tests/evaluation/test_policy_evaluation.py::test_missing_incompatible_exposed_or_noncontrolled_evidence_never_passes` [12], `::test_each_policy_split_needs_enough_independent_pairs_and_uncertainty`, `test_lifecycle.py::test_negative_evidence_cannot_promote` [6]. As evidence: not covered: needs an owner input (a private held-out set) | Unblinded, uncontrolled or one-split evidence passing | synthetic; native CI run; needs an owner input |
| 1 | Recorded exposure | `analysis.py:515-534`, `:272` | main `test_lifecycle.py::test_frozen_exposure_precedes_evaluator_and_cannot_be_repeated`, `test_recorded_evidence.py::test_evaluation_requires_durable_exposure` | Evaluation before recorded exposure, or twice | native CI run |
| 1, 3 | Predefined quality floors/tolerances | Calibration required and frozen before exposure, `evaluation.py:273-274`, `:320-322` | main the evaluation test. The values: not covered: needs an owner input (Q-12, Q-13) | Evidence passing without calibration fixed first | synthetic; native CI run; needs an owner input |
| 1 | Bounded rollout | `storage.py:285`; `analysis.py:665-667` | main `test_lifecycle.py::test_concurrent_routes_cannot_exceed_rollout_cap` | More concurrent routes than the authority's limit | native CI run |
| 1 | The release holdout remains untouched | `evaluation.py:314-315` | main the evaluation test (`release_holdout` refused) | A release-holdout case evaluated | synthetic; native CI run |
| 1 | Revalidate policies made stale by deletion | `storage.py:726-763`; `analysis.py:625-631` | main `test_lifecycle.py::test_deleted_supporting_data_invalidates_active_policy`, `::test_optout_only_invalidates_policies_using_the_affected_task` | A policy active after its data is deleted, or an unrelated one stale | native CI run |
| 1 | Regression rolls back affected scopes and suspends the version, with verified fallback | `analysis.py:639-662` | main `test_lifecycle.py::test_regression_restores_only_current_verified_previous_policy` | A regressed version left active, or a stale previous one brought back | native CI run |

**EC-EXPERIMENT-4** (`specs/phase-plans-v1.md:272`). Part 3: what the
criterion itself fixes and where `main` has each element; it adds no design.
Every clause is not covered: needs an owner input (a study authority). The
validator checks named are synthetic and cover nothing. Protocol:
`research/evaluation/discovery-calibration/protocol.json`; validator:
`validate_study`. A bare `:line` in this table is in
`scripts/verify_discovery_calibration.py`.

| P | Clause | On `main` | Validator check | Falsifier |
| --- | --- | --- | --- | --- |
| 3 | A preregistered development evaluation tests discovery and routing decisions against applicable CONTRACT baselines | The protocol's `baselines` and per-case `baseline_applicability`; marked `exposed`, not `promotion_eligible` | — | — |
| 3 | Ambiguous/cross-domain discovery, no useful optional guidance, objective changes, a skill with differing task needs | The cases' `scenario` values | — | — |
| 3 | Predeclare acceptable choices and independent outcome checks | Each case's acceptable guidance, model ids and expected result; `evaluation.py:102` | — | — |
| 3 | Known unsuitable controls must expose always-admit/all-default behavior | The protocol's `unsuitable_controls`, derived offline from its own checks without the application (`:285-306`) | — | — |
| 1, 3 | Report selection errors, downstream outcomes, total routing overhead and objective-specific cost/time/quality with uncertainty | `:469`, `:538` | main `tests/verification/test_discovery_calibration.py::test_produced_duration_accepts_complete_overhead_and_rejects_omission` [2], `::test_critical_regression_is_observed_but_missing_outcome_remains_unknown` | An omitted overhead component accepted; a missing outcome counted as a critical failure |
| 1, 3 | Executor bug-fixing scores alone cannot close this criterion | Each row needs discovery lineage (`:756-760`) | D new, SL-1 (Consiliency/jevdrill#77) | A record without discovery lineage accepted |
| 3 | Null results cannot justify benefit or promotion claims | `performance_claims` is `insufficient_evidence`; `promotion_authorized` must be false (`:731`) | — | — |

**Part 2: the restricted-runtime proof** (D, SL-3; needs a container). For
EC-EXPERIMENT-2's restricted containers, deadlines and absent runtimes: the
runtime verifier's named checks (`EXPECTED_CHECKS` at the tag, all 11 required),
among them container limits, worker custody, removal of the container and a
detached child after worker death, and an unavailable image refused. For pause,
cancel and the immediate path, and EC-EXPERIMENT-3's restricted grading: its
grader checks and the runtime tests of
`tests/experiments/test_development.py` [12, `RUNTIME_TESTS`] and
`tests/promotion/runtime_recorded_evidence.py::test_recorded_comparison_uses_restricted_grader`
[2], with the image. Falsifiers: a container with network, a writable root, a
capability, root or a mount; a process outliving its worker; a missing image
that readies; any of those tests failing, skipped or missing.

**Scope notes and gates**

| P | Item | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Freeze experiment transitions from CONTRACT (`specs/phase-plans-v1.md:276`) | `contracts.py:298-302` | main `tests/contracts/test_boundaries.py::test_terminal_events_and_experiment_authority_transitions` | `proposed` to `running` accepted | native CI run |
| 1 | JD-078's software clauses (`specs/phase-plans-v1.md:277`): reserve before a call | `experiments.py:231-240`; `integrations/development.py:282-285` | main `test_execution.py::test_admission_reserves_whole_run_without_dispatch_and_retries_reuse`, `tests/experiments/test_development_judge.py::test_uncertain_judgments_never_retry_refund_or_accept_wrong_model` [5] | A start or request with no reservation recorded first | native CI run |
| 1 | No retry or fallback | `experiments.py:334-338` | main the uncertain-judgment test, `test_development.py::test_development_provider_failures_never_retry` [3], `test_execution.py::test_lost_ack_restart_polls_without_redispatch`. Fallback: not covered; no test observes another endpoint | A second request after a failure or lost acknowledgment | native CI run |
| 1, 2 | Generated code requires restricted containers | As EC-EXPERIMENT-2 | As there | As there | As there |
| 1 | Policy promotion remains disabled | `application.py:1384-1386`; `analysis.py:372-373`; `evaluation.py:266` | main `test_lifecycle.py::test_no_configured_evaluator_cannot_register_or_self_authorize` (a default lifecycle refuses), `tests/cli/test_experiments.py::test_real_cli_blocks_critical_regression_without_promoting` | A default lifecycle that registers, or an assessment authorizing promotion | native CI run |
| 1 | EXPERIMENT reducer rejects invalid receipts (plan-level) | D `scripts/verify_experiment_phase.py` | D `tests/verification/test_experiment_phase.py::test_original_reducer_requires_current_native_controls` [12, plus one per new rejection], `::test_operational_reducer_requires_exact_named_checks_commands_image_and_artifacts` [6], `::test_reducer_rejects_missing_inherited_route_parameter` [one per inherited ROUTE control], `tests/verification/test_development_runtime.py::test_runtime_evidence_requires_every_test_successfully` [8], `::test_recorded_runtime_evidence_requires_both_controls`; D new: owner-input clauses reported not covered | A fault passing or not raising its own error; a valid receipt rejected | native CI run |
| 1, 2 | IF-0-EXPERIMENT-1 | Reducer: every clause covered, its controls passed where they run, three native receipts and the runtime receipt of one run, the inherited LEARN reduction without error | As the reducer | A gate produced with a clause not covered, a platform or the runtime job missing, or receipts of different runs | native CI run, no model called; needs the host integration; needs a container |

## Readings and points settled

- **JD-079** ("default to one background experiment at a time and two
  candidate plans per experiment", `specs/jevdrill-design-input.md:596`) is in
  this phase's coverage (`specs/phase-plans-v1.md:276`). `main` supplies no
  default: a proposal without either count fails schema validation
  (`experiments.py:403`, raised at `contracts.py:292`); no test shows it. On
  2026-11-22 the owner decided that this stands (`docs/contract-decisions.md`,
  "Changes to accepted decisions"). The plan verifies `main` as built;
  whether that meets the roadmap's sentence is the owner's at the gate.
- **Evidence kinds.** Fake-container tests are simulated
  (`tests/experiments/test_development.py:128-132`); policy-evaluation tests
  are synthetic. The roadmap: "Substitute/proxy evidence requires a
  runner-stamped roadmap amendment before a gate verdict"
  (`specs/phase-plans-v1.md:354`).
- **`inputs_unchanged`** in a run's acceptance checks
  (`integrations/development.py:982`) comes from the candidate's own process
  and can be forged (Consiliency/jevdrill#50). The grader ignores it
  (`tests/experiments/test_development_grader.py::test_independent_answer_grades_ignore_candidate_integrity_claims`);
  no row rests on it.
- **A recovery import blocks new experiment admissions** for its project and
  workspace, and nothing lifts the block (`storage.py:1272`;
  Consiliency/jevdrill#87): verified as built by
  `test_execution.py::test_portable_recovery_cannot_replenish_experiment_authority`;
  a stated limit.
- **No request leaves the runner.** Every control, old or new, is answered on
  loopback: a stand-in server on `127.0.0.1`, a replaced function or the fake
  container; none reads a credential. Two known breaks: the installed command
  line reaches the provider function, not a mock (`application.py:842`); the
  mock falls back to a public endpoint when its base URL is blank
  (Consiliency/jevdrill#17, open). Each lane says how it keeps this true.
- **No diagnostic mode.** The held `--software-only` mode goes (declared
  change 1).

## Cross-Repo Gate

This plan owns no path in `Consiliency/agent-harness`
(`specs/phase-plans-v1.md:192`) and pins nothing. The pin's conditions and
jevdrill's obligations are the HOST plan's "Cross-Repo Gate"; EXPERIMENT uses
HOST's pinned commit, and `experiment-phase.yml` follows J1 as that plan words
it.

**Where the evidence comes from.** One `workflow_dispatch` run of
`experiment-phase.yml` on hosted Linux, macOS and Windows runners, its runtime
job on hosted Linux. If hosted Linux cannot run the container, part 2 stays a
deliverable and no other runner is requested.

## Lane Index & Dependencies

- SL-1 — Tooling defect fixes; Depends on: (none); Blocks: SL-4; Parallel-safe: no
- SL-2 — Admission and runtime controls; Depends on: (none); Blocks: SL-4; Parallel-safe: no
- SL-3 — Runtime proof; Depends on: (none); Blocks: SL-4; Parallel-safe: no
- SL-4 — Verifier and workflow; Depends on: SL-1, SL-2, SL-3, LEARN's verifier lane on `main`; Blocks: SL-5; Parallel-safe: no
- SL-5 — Readiness doc; Depends on: SL-4 and one dispatched run; Blocks: (none); Parallel-safe: no

## Lanes

### SL-1 — Tooling defect fixes

- **Needs:** GitHub CI alone.
- **Owned files:** `scripts/verify_discovery_calibration.py`,
  `scripts/verify_calibration_benchmark.py`, their tests under
  `tests/verification/`, `src/jevdrill/integrations/development.py`,
  `tests/experiments/test_development_judge.py`,
  `tests/experiments/test_development_keys.py` (new), the driver paragraph of
  `docs/evaluation-protocol.md`.
- **Delivers:** fix lanes for Consiliency/jevdrill#77 (each fault on a
  complete record, asserting its own reason; the four untested refusals
  tested), #78 (its six defects; the dispatch guard as a property: nothing in
  code fixes an authority, model, price, cap or expiry, and with none supplied
  the driver refuses before reading a credential, making a directory or
  sending a request), #79 (the judge refuses an empty or missing credential
  before reserving or sending) and #47 (no stored observation contains the
  configured key). Fixing them grants and proposes nothing. Tests use
  synthetic keys and a stand-in server at an explicit `127.0.0.1` URL; none
  routes through the command line.

### SL-2 — Admission and runtime controls

- **Needs:** GitHub CI alone.
- **Owned files:** `tests/experiments/test_experiment_limits.py` (new).
- **Delivers:** the "D new, SL-2" controls, entered through `Experiments`,
  `Application` and `DevelopmentRunner`, with a stand-in server at
  `127.0.0.1` and the fake container or a replaced container client.
  `unit.yml` runs them unedited.

### SL-3 — Runtime proof

- **Needs:** a container; GitHub CI.
- **Owned files:** `scripts/verify_development_runtime.py`,
  `tests/verification/test_development_runtime.py`.
- **Delivers:** the held runtime verifier with declared changes 2 and 3, its
  tests passing in CI. Its job (SL-4's workflow) pulls the image by digest,
  records the local image id docker reports and passes it; it runs
  `tests/promotion/runtime_recorded_evidence.py`, which the verifier names by
  path. The container has no network (`integrations/experiments.py:66`); the
  stand-in server is at `127.0.0.1` (`tests/experiments/test_development.py:67`).

### SL-4 — Verifier and workflow

- **Needs:** LEARN's verifier lane on `main` (this verifier loads LEARN's,
  which loads HOST's), HOST's pinned commit, SL-3; GitHub CI.
- **Owned files:** `scripts/verify_experiment_phase.py`,
  `tests/verification/test_experiment_phase.py`,
  `.github/workflows/experiment-phase.yml` (new),
  `evidence/EXPERIMENT/coverage.json`, `evidence/EXPERIMENT/spec-delta.json`,
  the EXPERIMENT lines of `.gitignore` and
  `tests/verification/test_route_phase.py`.
- **Delivers:** the held verifier and tests with every declared change; the
  workflow, dispatch only, `permissions: contents: read`, no secret, no
  registry login, its reduce job needing the three native jobs and the runtime
  job. Its writer dispatches it on `main` with the pinned SHA. Collections keep
  loopback as in the HOST and LEARN plans. `experiment.yml` keeps its triggers
  as the offline diagnostic; no workflow a pull request or push triggers checks
  out the host integration or pulls an image.

### SL-5 — Readiness doc

- **Needs:** SL-4's run, with its verdict artifact if there is one.
- **Owned files:** `docs/experiment-readiness.md`.
- **Delivers:** the held doc rewritten: the run linked, with its verdict as
  that run's artifact or why it has none; the not-covered clauses and owner
  inputs; no
  October receipt, image or study record.

## Verification

Runs on `main` today (the second line with the pinned compiler that
`contracts.yml` installs):

```sh
uv run python -m pytest -q tests/experiments tests/promotion tests/storage/test_experiments.py tests/application/test_experiments.py tests/cli/test_experiments.py tests/verification/test_discovery_calibration.py
uv run python -m pytest -q tests/evaluation/test_policy_evaluation.py tests/contracts/test_boundaries.py::test_terminal_events_and_experiment_authority_transitions
```

Deliverables (the verifier commands are `experiment-phase.yml` steps):

```sh
uv run python -m pytest -q tests/experiments/test_experiment_limits.py tests/experiments/test_development_keys.py
uv run python -m pytest -q tests/verification/test_experiment_phase.py tests/verification/test_development_runtime.py
uv run python scripts/verify_experiment_phase.py --local-only --agent-harness .host/companion
uv run python scripts/verify_development_runtime.py --image-id <local image id of the pinned digest>
uv run python scripts/verify_experiment_phase.py --reduce-only --agent-harness .host/companion
gh workflow run experiment-phase.yml --repo Consiliency/jevdrill --ref main -f companion_ref=<40-hex commit SHA>
```

Effective `automation.suite_command`: `uv run python scripts/verify_experiment_phase.py --agent-harness .host/companion` (deliverable; a missing companion fails closed).

## The verifier

**It must check,** under the verifier rules of the HOST and LEARN plans, the
tables' controls; the inherited LEARN reduction; the same run's runtime
receipt, naming the image digest and local id, every named check and the
runtime and recorded tests with exact counts; module provenance; the coverage
record and a `no_spec_delta` closeout; the 600-second bound, flagging proof
over five minutes.

**One rule for this plan.** A clause whose only possible control is a study
record or an owner-set value is reported "not covered: needs an owner input",
names the input, and blocks IF-0-EXPERIMENT-1 like any other. The whole-phase
verdict therefore stays `blocked` by design until the owner inputs exist.
IF-0-EXPERIMENT-1 is also not produced while IF-0-LEARN-1 would not be; today
five HOST clauses and one LEARN clause are not covered.

**It reads** the jevdrill checkout, the companion at HOST's pinned commit and
the runtime job's receipt; no study record, proposal or authorization, and
nothing in their place that records a grant. **It writes**
`evidence/EXPERIMENT/platforms/` and `evidence/EXPERIMENT/verification.json`,
ignored by git. A verdict is the CI artifact of the run that made it and is
never committed.

**Declared changes to the held instruments:**

1. `empirical_errors`, its two study files, the study proposal in
   `input_digest` and the `--software-only` mode go; owner-input clauses are
   reported under the rule above. Reason: the study records are not restored,
   and that mode skipped only `empirical_errors` and could report `passed`.
2. The runtime receipt comes from a job of the same run, written outside the
   checkout; the reducer reads no other. Reason: Consiliency/jevdrill#73.
3. The fixed image id of the runtime verifier and of
   `scripts/verify_discovery_calibration.py:417` gives way to the pinned
   digest and the local id recorded from it. Reason: the October image has no
   registry reference.
4. `CONTROLS` and the coverage record become the tables' controls with exact
   counts; the three tests Consiliency/jevdrill#80 names are not controls.
   Reason: the verdict binds the rows; Consiliency/jevdrill#71.
5. Each reducer fault asserts its own error; a malformed receipt is reported,
   not raised; tests build receipts from constants, reading no committed
   receipt or verdict. Reason: a fault any error satisfies cannot fail;
   October's files are not restored.
6. `experiment-phase.yml` as SL-4 states, with pinned actions, `route.yml`'s
   "Require successful native jobs" and ignore rules for every path written;
   it joins the two reduction tests of `test_route_phase.py`. Reason: no
   workflow ran this verifier at the tag; Consiliency/jevdrill#74.
7. The spec-delta record is re-made in the roadmap's words. Reason: the tag's
   names paths the roadmap does not.

## Acceptance Criteria

- [ ] EC-EXPERIMENT-1, EC-EXPERIMENT-2, EC-EXPERIMENT-3, EC-EXPERIMENT-4 — by
  the controls and falsifiers of the clause tables, reduced by SL-4's verifier
  from one run.

## This plan may not claim

- Any criterion verified or gate produced; IF-0-EXPERIMENT-1 before LEARN
  evidence exists (`specs/phase-plans-v1.md:350`).
- Anything on the strength of the September or October records.
- That a study is authorized, proposed or able to run.
- Any empirical result, calibrated tolerance or model quality.
- That the offline report or any synthetic or simulated evidence satisfies a
  criterion, the suite or the phase.
- Any promotion.
- That hosted runners can run the host integration or the container; that the
  host integration is accepted or carries a comparison path.
- That a fake-container test shows isolation, or `inputs_unchanged` unchanged
  inputs.
- That a recovery import's experiment block can be lifted.
- That a decline starting no run is visible to learning; that LEARN evidence
  informs later discovery or selection; that synthetic HOST receipts are more
  than software conformance.
- Ratified review, publication, adoption or release readiness.

## Attached backlog

| Item | Disposition |
| --- | --- |
| Consiliency/jevdrill#77, #78, #79, #47 | Fix lanes, SL-1 |
| Consiliency/jevdrill#80 | EC-EXPERIMENT-4's controls named afresh; declared change 4 |
| Consiliency/jevdrill#50 | Stated limit; no row rests on the flag |
| Consiliency/jevdrill#87 | Verified as built; stated limit |
| The image; the held evidence inputs; malformed receipts and receipt-building tests; the runtime proof that `docs/contract-decisions.md:48` says is not run | Declared changes 1 to 3, 5 and 7; SL-3 and SL-4 |
| Blocked by design until the owner's inputs | The rule under "The verifier" |
| ROUTE verifier not reopened except for a defect this verifier exposes; the deadline-failure rule | Stated limits, standing |

## Owner inputs

None is asked here; each blocks what it names.

- **Who takes the host integration to a merged state**, as in the HOST plan.
  Without it only SL-1 to SL-3 can run.
- **The Q-12 and Q-13 tolerances.** Without them EC-EXPERIMENT-3's floors and
  tolerances and every EC-EXPERIMENT-4 clause stay not covered.
- **A study authority naming every number anew**: models, prices, caps,
  budget, expiry and provider credentials. Without it every EC-EXPERIMENT-4
  clause stays not covered and nothing calls a provider.
- **A private held-out set.** Without it EC-EXPERIMENT-3's blinded evaluation
  has no evidence and no quality or benefit claim is made.
- **A promotion authority.** Without it no policy is promoted.
- **A container host**, only if hosted Linux cannot run the container.
  Without it part 2's rows block the gate.
- **Closing the EXPERIMENT gate**, including whether simulated and synthetic
  evidence satisfies EC-EXPERIMENT-2 and 3 under `specs/phase-plans-v1.md:354`,
  and each software clause not covered.

Owner decisions on `main`: `docs/contract-decisions.md`, "Changes to accepted
decisions", whose JD-043 paragraph keeps separate authorization for external
providers in background experiments.

## Execution Notes

Execute serially, one writer per lane; each lane's scope is fixed before it is
cut and reviewed as this plan was. No edit to `specs/phase-plans-v1.md`,
`plans/manifest.json` or `scripts/verify_route_phase.py` beyond the backlog's
standing limits. Tests use synthetic stores and keys only. No study is
planned; one would be added by amendment after the owner's authority.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`; decision: `no_spec_delta`
- target surfaces: experiment/promotion contracts; evidence paths: `evidence/EXPERIMENT/spec-delta.json`
- redaction_posture: `metadata_only`; missing/malformed evidence: `blocker_class=contract_bug`, non-human repair.
