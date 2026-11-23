---
phase_loop_plan_version: 1
phase: LEARN
roadmap: specs/phase-plans-v1.md
roadmap_sha256: 4ecbf27188b634d6ea5346cd67d61ab36d50d3ad0416a9a6d0d2602bb2698ab8
---

# LEARN: Local learning and maintenance

> Review status: draft written by Claude Opus 5.5. Board: a Fable 5.2 president
> and three seats (correctness, security and privacy, alternate vendor); one
> round and a confirmation. Pull request: Consiliency/jevdrill#92; amended by
> #122 (SL-7), #126 and #131 (SL-8), and #143 (SL-9). A reviewed plan; it verifies
> no criterion.

## Context

This plan revises LEARN against the amended roadmap, EC-LEARN-1 to 5 and
IF-0-LEARN-1. The October plan at the tag `pr1-final-record` was reviewed only
by its planner and is not accepted as the required revision.

The LEARN code is on `main`: the roadmap's two lanes have landed, and the nine
here are what remains. SL-1 to SL-3 and SL-7 to SL-9 need only GitHub CI; the rest
waits for the host integration and HOST's verifier. Nothing here runs a
collector, requests a host run, spends money or closes a gate.

Length exception: every clause is mapped to code, control, falsifier and
evidence kind.

## State of `main` at `d58e52e85`

`unit.yml` runs the LEARN tests on three platforms, deselecting for good the
one that needs the host integration,
`tests/application/test_learning.py::test_installed_discovery_host_tasks_reports_analysis_and_entered_denials`.

**Held at the tag, not on `main`:** SL-4's verifier, tests and workflow, and
`docs/learn-readiness.md`. October's evidence is not restored; SL-4 and SL-5
remake its records, and receipts, verdicts and history are never committed.

**Exists nowhere:** an accepted host-integration commit, a hosted LEARN
receipt or expected-test list, the controls marked "D new", or use of an
installed scheduler or real key store.

## External Inputs

- Host integration, inspected: the draft in the HOST plan.
- JEV Drill on Python 3.14 (`pyproject.toml:9`); BAML `baml-language-0.20.1`
  and `baml-bridge==0.20.1`; `cryptography` 50.0.2 and `keyring` 25.7.0 as
  locked in `uv.lock`, within `pyproject.toml:10`.
- Key stores (macOS Keychain, Windows Credential Locker, Linux Secret Service)
  and schedulers (systemd, launchd, Task Scheduler): untested targets.
- Read inputs: `main`, the tag and the draft; no corpus, holdout, credential,
  provider log, user database or private repository.

## Interface Freeze Gates

- [ ] IF-0-LEARN-1 — Comparable evidence updates, maintenance and retention
  lifecycle.
- Consumed: IF-0-HOST-1, as the HOST plan defines it.

## Criteria, clause by clause

Key as in the HOST plan ("main", "D", "D new", "HI"; HI files are under
`phase-loop-runtime/tests/`). A bracketed count is the exact number of cases
required. A test named once by full id is then named by its subject. Sources
are under `src/jevdrill/` unless a path says otherwise. Nothing below is
verified.

**EC-LEARN-1**

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Versioned comparable groups | Key `analysis.py:681` over conditions `storage.py:925-980`; metrics `analysis.py:687-689` | main `tests/analysis/test_observations.py::test_incompatible_contexts_never_aggregate_across_domains` [6], `::test_metric_revisions_units_methods_remain_separate` | Two revisions or metric definitions merged in one group | native CI run |
| Minimum batches and periodic triggers update evidence | `application.py:1306-1323` | main `tests/application/test_learning.py::test_analysis_batch_interval_objective_history_and_immutable_replay` (below the batch, `not_due`; after the interval, `updated`), `::test_settings_optout_exclusions_and_disabled_model_analysis_enter_application` (a batch of one met) | A trigger that never fires, or fires below the batch before the interval | native CI run |
| Under existing policy | Only learning tables written, `storage.py:1050-1087` | main the settings test (analysis calling `Application.route` fails); D new, SL-3: no policy record written | A policy record written, or a route made, by analysis | native CI run |
| Reassessment supports multiple objectives without inventing counterfactual results | `application.py:1314-1318`; `analysis.py:745-747` | main the batch test, `test_observations.py::test_substitution_preference_and_evaluation_are_distinct` | A classification other than `insufficient_evidence`, or groups changed by reassessment | native CI run |
| Missing, failed and canceled observations remain explicit | `analysis.py:692-701`, `:709-725` | main `test_observations.py::test_missing_failed_canceled_corrected_and_unknown_observations` | A canceled run counted as failed, or an unknown value averaged | native CI run |

**EC-LEARN-2**

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Scheduled maintenance prevents overlap | `integrations/archive.py:69`, taken `maintenance.py:112-115` | main `tests/maintenance/test_maintenance.py::test_process_owned_nonoverlap_and_exit_release` | A second run while the lock is held, or a lock outliving its process | native CI run |
| Resumes safely | Cursor `maintenance.py:131-135`, `:225-231` | main `test_maintenance.py::test_bounded_resumable_cursor_pause_cancel_and_interactive_contention`; D new, SL-2: the store reopened before resume | An item missed or processed twice after pause, cancel, reopening and resume | native CI run |
| Yields to interactive work | `maintenance.py:109-111`, `:148-152` | main same test; `test_maintenance.py::test_pause_and_interactive_start_are_rechecked_between_production_items`; `tests/cli/test_learning.py::test_native_scheduler_argv_enters_installed_maintenance_and_host_contention` | An item processed after the host marks itself busy | generated configuration; native CI run |
| Scheduler, pause and cancel evidence on Linux, macOS and Windows | `maintenance.py:262-364`; command `:289-298` | main the scheduler test (the generated entry's command, parsed and run natively), the cursor test; D new, SL-2: the generated entry recurs; a module planted under a standard-library name in the job's working directory is not imported (Consiliency/jevdrill#52) | A generated entry whose parsed command fails or that never recurs, or the planted module imported | generated configuration; native CI run |
| Deterministic analysis is default | `analysis.py:678-749`; `settings.py:25-27` | main the settings test | Any analysis but the deterministic one obtained | native CI run |
| Model-assisted analysis requires enabled capability and budgets | No such mode: `AnalysisRequest` has no field for it (`baml_src/contracts.baml:183-187`) | main the settings test (a mode field with a budget refused) | A model-assisted request accepted | native CI run |

**EC-LEARN-3**

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Clock and key-failure fixtures on three platforms | `maintenance.py:124-125`, `:76-80`; `integrations/archive.py:28` | main `tests/retention/test_retention.py::test_clock_rollback_and_corruption_enter_production_retention`, `::test_key_failures_keep_pending_active_content_and_notice` [3], `test_maintenance.py::test_os_key_store_failure_is_bounded_without_plaintext_fallback` | Retention after the clock moves back, or content lost when the key fails | simulated; native CI run |
| 30-day active retention, seven-day archive grace | `maintenance.py:160-169` | main `test_retention.py::test_active_grace_encrypted_archive_one_year_expiry_and_measurement_persistence` | A prompt before day 30, or archival before seven more days | native CI run |
| Encrypted archival; never archive unencrypted | `maintenance.py:170-224`; `integrations/archive.py:17-24` | main the active-grace and key-failure tests, `test_retention.py::test_archive_crash_retry_keeps_source_until_durable_verification`, `::test_archive_tamper_cannot_restore` | Plaintext in an archive, or an archive made without a key | simulated; native CI run |
| One-year expiry notices | `maintenance.py:153-159` | main the active-grace test; D new, SL-2: a failing item leaves the others on time (Consiliency/jevdrill#45); re-archived content expires and is announced one year after its first archival (#46); D new, SL-8 | A notice missing or misdated before expiry; a restored copy archived after its earlier archive expired, lost before a year from that archival; an earlier failing item unreported or abandoned; later healthy content kept past expiry; unverified content retired | native CI run |
| Restoration | `maintenance.py:366-401` | main `tests/maintenance/test_recovery.py::test_native_archive_restore_and_portable_archive_export`, the tamper test; D new, SL-3: restored bytes equal the original | Restored bytes that differ, or a tampered or deleted archive restored | native CI run |
| Deletion propagation | `storage.py:1045-1049`; `delete_task` `storage.py:2384-2397` | main the active-grace and native-restore tests; `test_observations.py::test_source_digest_recheck_prevents_deleted_analysis_commit`; `tests/storage/test_learning.py::test_deletion_preserves_unrelated_project_evidence_and_objective_history`; D new, SL-2: deletion while another connection reads (Consiliency/jevdrill#21); an archived copy's file gone after task deletion; D new, SL-9 | Deleted content, archived copies included, left on disk, readable or analysed; `deleted` reported while a payload stays in the write-ahead log, or erasure still incomplete after the reader closes and deletion is retried; metadata or a notice of a deleted discovery left in the store | native CI run |
| Missing credentials, headless Linux included, keep content pending with notices | `maintenance.py:170-173`; `storage.py:2311` | main the key-failure test [3] | Content removed, or no notice, without a key | simulated; native CI run |
| Inspectable export, import and backup verify integrity and portable keys | `maintenance.py:403-439`; `storage.py:1115`, `:1211` | main `test_recovery.py::test_portable_export_backup_import_preserves_lineage_and_deletion_precedes_sources`, `::test_malformed_or_conflicting_import_rejects_transactionally` [6] | A tampered or conflicting bundle importing anything | native CI run |
| Deletion records applied before restored or imported analysis | `storage.py:1211` | main the portable-export test; `test_recovery.py::test_imported_optout_never_reenables_analysis_or_policy_validation`; D new, SL-3: a backup's own deletion records honoured in a fresh store | A tombstoned objective or task, or an opted-out task, analysed after import | native CI run |
| Redacted measurements persist until deletion | Credential check before persistence, `application.py:1230` | main the active-grace test; `tests/privacy/test_round41_learning.py::test_report_sensitive_map_key_rejects_before_persistence` | A measurement lost at archive expiry, kept after deletion, or stored with credential-like text | native CI run |
| Policy validation becomes stale without automatic rollback | `storage.py:726-763` | main the imported-opt-out test; `tests/promotion/test_lifecycle.py::test_deleted_supporting_data_invalidates_active_policy` (stale; ordering blocked); D new, SL-3: with an earlier verified policy, none restored | Validation left current, or a previous policy restored, after its data changed | native CI run |

**EC-LEARN-4**

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Persistent local notices | Written `maintenance.py:56-61`, read `storage.py:2311` | main the key-failure test [3] (notices read back from the store); D new, SL-2: read again after reopening it | A notice lost after its run or after reopening | simulated; native CI run |
| Opt-out and exclusion controls work | `application.py:1270-1275`; `storage.py:765-775`, `:800-801` | main the settings test, `tests/privacy/test_learning.py::test_default_workspace_scope_and_explicit_redacted_user_wide_consent`, `tests/storage/test_learning.py::test_restart_migration_evidence_history_and_optout` | An excluded or opted-out task analysed, or evidence drawn from it before the opt-out kept | native CI run |
| Sharing project-scoped by default, user-wide only by explicit opt-in | `storage.py:857-859` | main the privacy test (nothing seen without both consents) | An observation shared without producer or requester consent | native CI run |
| User-wide learning is redacted | `storage.py:994`, `:997`, `:1008-1010`, `:1022-1030` | D new, SL-1 and SL-7 (the privacy test checks keys an observation never has, so shows no redaction) | Any failure SL-1's or SL-7's control names | native CI run |
| Benchmark assessments retain source metrics and objective history | `analysis.py:687-701`; objective history `application.py:1283-1286` | main `test_metric_revisions_units_methods_remain_separate`, the missing-failed test (source measurement kept), the batch test, `test_deletion_preserves_unrelated_project_evidence_and_objective_history` | A metric definition or prior objective version lost | native CI run |

**EC-LEARN-5**

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Observations link discovery choices and task configurations to actual outcomes | `storage.py:777-797`, `:945-998` | main `test_observations.py::test_terminal_applied_ids_corrections_and_unrelated_runs_remain_authoritative`, `::test_no_guidance_discoveries_keep_authoritative_boundaries_despite_forged_family_labels`, `tests/storage/test_learning_lineage.py::test_forged_learning_link_enters_storage_and_is_rejected` [4], `::test_cross_producer_objective_tombstone_suppresses_analysis_but_keeps_task_reports`; main, deselected, needing the host integration: `test_installed_discovery_host_tasks_reports_analysis_and_entered_denials` with the reducer's witness check | A forged, missing or deleted link analysed; two tasks merged; an applied identity from the caller | native CI run; needs the host integration |
| Comparable evidence can inform later discovery and task selection | None | Not covered: no path carries LEARN evidence into `DiscoveryInputs` (`baml_src/discovery.baml:24-31`) or into selection, which reads only host-supplied candidate evidence and authorized ordering (`routing.py:241`, `:253`); no test sends it either way; no contract change is planned | — | needs an owner input |
| Missing data, host preference, substitutions and measured failures stay distinct | `storage.py:1014-1018`; `analysis.py:709-730` | main the substitution and missing-failed tests | One of the four counted as another | native CI run |
| Reclassification preserves raw measurements and prior objective versions | `application.py:1283-1286` | main the batch test (groups equal; both versions kept) | Groups recomputed or a version dropped on reclassification | native CI run |
| No unsupported whole-skill or cross-domain claims | `analysis.py:745-747` | main the incompatible-contexts test [6], the substitution test, `tests/cli/test_learning.py::test_installed_cli_analyze_notices_recovery_and_reject_unknown_claims` (a `whole_skill` request refused by strict parsing) | An assessment classed `observed`, or a group spanning task families | native CI run |
| Policy writes limited to authorized candidate ordering; no learned navigation change | As "under existing policy" | D new, SL-3: on identical inputs, analysis changes no later discovery or route result | A policy write, or a discovery or route result that differs on identical inputs after analysis | native CI run |

**Gates**

| Item | Control | Falsifier | Evidence |
| --- | --- | --- | --- |
| Companion extras | HI `test_windows_locking.py`, `test_launcher_liveness.py`; on Windows also `test_windows_processes.py`, `test_windows_storage.py`; collected ids equal to that platform's list (SL-5) | An id missing, extra, duplicated or not passed | native CI run; needs the host integration |
| LEARN reducer rejects invalid receipts (plan-level) | D `tests/verification/test_learn_phase.py::test_reducer_rejects_missing_stale_wrong_origin_and_boolean_substitutes` [21, plus one per new rejection], `::test_reducer_accepts_complete_synthetic_input`, `::test_reducer_binds_sorted_groups_and_applied_alternatives_to_authoritative_runs` [3], `::test_windows_extra_command_requires_process_and_storage_controls`, `::test_reducer_rejects_missing_inherited_route_parameter` [one per inherited ROUTE control] | A fault that passes or does not raise its own error, a receipt missing an inherited ROUTE control passing, or a valid one failing | native CI run |
| IF-0-LEARN-1 | Reducer: every clause covered, its controls passed where they run, three receipts of one run, their HOST part reduced without error | A gate produced with a clause not covered, a platform missing, receipts of different runs or the HOST part failing | native CI run, no model called; needs the host integration |

## Readings and points settled

- **The HOST handoff.** LEARN is planned against metadata-only objective,
  discovery, task, decision and run bindings and durable objective tombstones.
  It distinguishes selected from applied plans, independent task deletion,
  unknown usage and host retain or decline preferences.

  Each maps to clause rows: metadata-only bindings and selected versus applied
  to EC-LEARN-5's first row; objective tombstones to that row and to
  EC-LEARN-3's deletion records; independent task deletion to EC-LEARN-3's
  deletion propagation and EC-LEARN-5's first row; unknown usage to
  EC-LEARN-1's last row; retain or decline to EC-LEARN-5's third.

- **Deterministic analysis is default** is read as the mode: the only
  analysis is deterministic, run where settings enable it. `main` has local
  analysis and raw retention off by default (`settings.py:23-25`). JD-043 said
  on by default with opt-out (`specs/jevdrill-design-input.md:358`); on
  2026-11-22 the owner decided that off by default stands
  (Consiliency/jevdrill#94). This plan verifies `main` as built. Model-assisted analysis does not exist and a request for
  it is refused (`docs/learn-interfaces.md:35-36`): a condition on a
  capability, whose control is the refusal. Nothing builds it.
- **Benchmark assessments** are read as analysis's objective assessments,
  which keep source metric definitions and objective versions as the nearest
  text asks (`docs/jevdrill-spec.md:202-214`). Published benchmark scores are
  ROUTE catalog inputs (`baml_src/contracts.baml:136-137`), outside the clause.
- **Evidence kinds.** The scheduler evidence is generated configuration: the
  written entry is parsed and its command run natively; nothing is installed.
  Every archive key and key-store state is simulated, by an injected key
  provider or by a replaced `subprocess.run` under `archive_key`
  (`tests/maintenance/test_maintenance.py:94-105`); `missing` stands for
  headless Linux, and `locked` behaves identically. The roadmap's rule stands beside both:
  "Substitute/proxy evidence requires a runner-stamped roadmap amendment before
  a gate verdict" (`specs/phase-plans-v1.md:354`).
- **Needing the host integration:** the installed control and the four
  companion files. The files run whole, with no skip where they run (the
  Windows two only on Windows), and may not carry `dotfiles_integration`. The four
  files are host-platform regressions, cited for no LEARN clause; the installed
  control is EC-LEARN-5's.
- **Re-archived content (Consiliency/jevdrill#46)** reuses the first archive
  and its time (`maintenance.py:188-197`; `storage.py:2202`), so content
  archived again before that archive expires keeps its expiry; "Cold archives
  expire one year after archival" (`specs/jevdrill-design-input.md:364`) is
  read so.

## Cross-Repo Gate

This plan owns no path in `Consiliency/agent-harness`
(`specs/phase-plans-v1.md:192`). The pin's conditions and jevdrill's
obligations are the HOST plan's "Cross-Repo Gate". LEARN uses the same pinned
commit and handoff record and pins nothing itself; `learn.yml` follows J1 as the
HOST plan words it; SL-5 makes the lists of J4.

**Where the evidence comes from.** Two dispatched `learn.yml` runs on GitHub's
hosted Linux, macOS and Windows runners; a verdict rests on one. The HOST plan's conditional host run
applies on its terms: a possibility, not a request.

## Lane Index & Dependencies

- SL-1 — Shared-record fingerprint; Depends on: (none); Blocks: SL-4; Parallel-safe: no
- SL-2 — Deletion, retention and scheduler fixes; Depends on: (none); Blocks: SL-4; Parallel-safe: no
- SL-3 — LEARN-side controls; Depends on: (none); Blocks: SL-4; Parallel-safe: no
- SL-4 — Verifier and workflow; Depends on: SL-1, SL-2, SL-3, SL-7, SL-8, SL-9, HOST's verifier lane on `main`; Blocks: SL-5; Parallel-safe: no
- SL-5 — Expected-test lists; Depends on: SL-4 and one dispatched run; Blocks: SL-6; Parallel-safe: no
- SL-6 — Readiness doc; Depends on: SL-5 and one dispatched run; Blocks: (none); Parallel-safe: no
- SL-7 — Revisions digest in shared records; Depends on: SL-1; Blocks: SL-4; Parallel-safe: no
- SL-8 — Restored content kept; Depends on: SL-2, SL-7; Blocks: SL-4; Parallel-safe: no
- SL-9 — Discovery erasure; Depends on: SL-8; Blocks: SL-4; Parallel-safe: no

## Lanes

### SL-1 — Shared-record fingerprint

- **Needs:** GitHub CI alone.
- **Owned files:** `src/jevdrill/storage.py` (`learning_observations`),
  `tests/privacy/test_shared_records.py` (new), the sentence of
  `docs/learn-interfaces.md:12-15`.
- **Delivers:** fix lane for Consiliency/jevdrill#86, as the owner decided on
  2026-11-22: the fingerprint in shared records becomes specific to the
  requesting project. In an observation whose source is `user_wide_redacted`,
  `discovery_identity` and the observation reference are treated the same: each
  becomes specific to the requester and stable for it, so the batch trigger's
  comparison of references (`application.py:1308-1320`) still counts new
  observations and one discovery's observations still share a group. Local
  observations are unchanged. Both stay strings: no contract or schema change
  (`baml_src/contracts.baml:193-200`). The new control, with one producer and two requesters, all consenting, fails
  if a user-wide source names a producer identity; if either value can be
  recomputed from the producer's inputs (`storage.py:994`, `:1008-1010`) and
  the requester's identifiers without the requester's store; if the two
  requesters receive an equal value; if a requester's values change between
  two analyses; or if one discovery's observations stop sharing a group.
  Evidence stored earlier keeps its values until replaced; the doc says so.

### SL-2 — Deletion, retention and scheduler fixes

- **Needs:** GitHub CI alone.
- **Owned files:** `src/jevdrill/storage.py` (`delete_task` and what it calls),
  `src/jevdrill/maintenance.py`, `tests/maintenance/test_lifecycle_faults.py`
  (new), `tests/storage/test_wal_erasure.py` (new), the scheduler and retention
  paragraphs of `docs/learn-interfaces.md`.
- **Delivers:** fix lanes for Consiliency/jevdrill#21 (`delete_task` stops
  reporting complete deletion while a deleted payload stays in the write-ahead
  log, and completes on retry once the reader closes), #45 (an earlier item
  failing on every run is reported and retried without stopping the others;
  nothing unverified is retired), #46 (as read above) and #52 (the generated
  command imports nothing from the job's working directory). New controls also
  show an archived copy's file gone after task deletion, the generated entry's
  recurrence, and the cursor and notices surviving a reopened store. A fix that changes a response is a declared contract change
  under CONTRACT's compatibility rules.

### SL-3 — LEARN-side controls

- **Needs:** GitHub CI alone.
- **Owned files:** `tests/application/test_learning_limits.py` (new).
- **Delivers:** controls entered through `Application`: analysis and the
  maintenance follow-up write no policy record and, on identical inputs, change
  no later discovery or route result; import and restore write saved text back as saved, unchecked,
  also with raw retention off (Consiliency/jevdrill#53, as ratified); a
  completed maintenance run whose follow-up analysis refuses stored objectives
  answers `invalid_input` with its work committed (#58, as ratified); deleting
  a promoted policy's supporting data restores no earlier verified policy;
  restored bytes equal the original; a backup's own deletion records are
  honoured in a fresh store. `unit.yml` runs them unedited.

### SL-4 — Verifier and workflow

- **Needs:** HOST's verifier lane on `main` (this verifier loads it) and its
  pinned commit; GitHub CI.
- **Owned files:** `scripts/verify_learn_phase.py`,
  `tests/verification/test_learn_phase.py`, `.github/workflows/learn.yml`,
  `evidence/LEARN/coverage.json`, `evidence/LEARN/spec-delta.json`, the LEARN
  lines of `.gitignore` and `tests/verification/test_route_phase.py`, and
  the installed test of `tests/application/test_learning.py`, only to fit the
  pinned commit's fixtures, keeping its checks and witness; if the pin cannot
  support them, that row is not covered.
- **Delivers:** the held verifier, tests and workflow with every declared
  change below; its reducer tests pass in CI. They fail if a part over its
  bound, parts not summing to the collection's time, or a receipt lacking part
  times passes; a control is missing or counted
  from two sources; the inherited call differs from HOST's; the inherited
  interval is not the HOST call's, start to return; or a LEARN
  child sees more than HOST's child allowlist and an empty home, or the HOST call
  starts from a changed environment. On `main`, its writer
  dispatches `learn.yml` with the pinned SHA and records the run, which has no
  lists yet and so produces no gate.

### SL-5 — Expected-test lists

- **Needs:** SL-4 and its dispatched run.
- **Owned files:** `evidence/HOST/companion/extra-Linux.json`,
  `extra-Darwin.json`, `extra-Windows.json`.
- **Delivers:** each list from the ids that platform's receipt in that run
  collected: repository, commit, platform and ids, no path or command. None is
  made off a hosted runner. The correctness seat of the pull request that
  commits them checks each id against the test files at the pinned commit; a
  second run, dispatched by this lane's writer with the same pin once the lists
  are on `main`, is reduced against them. Without three valid receipts from the
  first run there are no lists.

### SL-6 — Readiness doc

- **Needs:** SL-5's run and its verdict artifact, if any.
- **Owned files:** `docs/learn-readiness.md`.
- **Delivers:** the held doc rewritten: the second run linked, with its verdict
  as that run's artifact (as in `docs/route-readiness.md`) or why it has none;
  no dotfiles fixture; counts recounted or removed; no October receipt.

### SL-7 — Revisions digest in shared records

- **Needs:** GitHub CI alone.
- **Owned files:** `src/jevdrill/storage.py` (`learning_observations`),
  `tests/privacy/test_shared_records.py`, the paragraph of
  `docs/learn-interfaces.md` that SL-1 changed.
- **Delivers:** fix lane for Consiliency/jevdrill#86. In a user-wide
  observation, `discovery_revisions` is an unkeyed digest of the discovery's
  revisions (`storage.py:1024` at `83cfe464c`). Their `authorization_digest`
  covers the producer's discovery scope, constraints, attachments and required
  guidance (`application.py:191-193`), so the value differs between producers
  and is equal for every requester and store. It is treated as SL-1's two values
  are: keyed with the store's key and the requesting scope, in the same form.
  Local observations are unchanged; no contract or schema change. The control
  fails if the value can be recomputed without the store's key; if two
  requesters, or two independently created stores, receive an equal value; if a
  requester's value changes between two analyses; if, for one requester and
  store, observations with unequal revisions receive an equal value or with
  equal revisions unequal values; if two user-wide observations of one discovery
  stop sharing a group; or if a local observation's value changes. Evidence
  stored earlier keeps its values until replaced, and a store rebuilt from a
  recovery export gives different values; the doc says so.

### SL-8 — Restored content kept

- **Needs:** GitHub CI alone.
- **Owned files:** `src/jevdrill/maintenance.py` (archiving restored copies;
  retiring archives), `src/jevdrill/storage.py` (only where an archive row is
  reused), `tests/maintenance/test_lifecycle_faults.py`, the sentence of
  `docs/learn-interfaces.md` naming #125.
- **Delivers:** fix lane for Consiliency/jevdrill#125 (at `5ba5e62e9`:
  `maintenance.py:395`, `:249`, `:212`, `:157-159`; `storage.py:2232`). A
  restored copy archived after its earlier archive has expired, by the rule of
  `maintenance.py:157`, expires one year after that archival, whatever the order
  and timing of runs. For Consiliency/jevdrill#128, for an archive the run's
  filters admit, in any page, while the archive is still in its last seven
  days: the first run, unless paused, cancelled or busy at start, writes its
  notice; a run out of time keeps those it wrote, following runs the rest
  (#139). Retirement never waits for one. No contract or schema change. The control
  fails if the content cannot be restored with its original bytes before a year
  from that archival, or still can after a run past that year: in #125's
  sequence in either order, with the two items reached in different runs, or at
  the archive's exact deadline; if content restored and archived again before
  the archive expires stops keeping that expiry; if such a run leaves no expiry
  notice, or a run keeps an expired archive for want of one; or if anything
  unverified is retired.

### SL-9 — Discovery erasure

- **Owned files:** `src/jevdrill/storage.py` (`delete_discovery`, import of
  deletion records, their callees), `tests/storage/test_discovery_erasure.py`
  (new).
- **Delivers:** fix lane for Consiliency/jevdrill#138, the metadata issue
  (opened at #141's merge) and #21's `delete-discovery` half. A finished
  deletion, requested or imported, leaves neither the discovery's recovered
  metadata nor a notice row naming its items in the store's files; until then
  it answers as `delete_task` since SL-2. No contract or schema change. The
  control fails if, after a finished deletion, its domain label is
  in a store file, an item identity of it in a notice, or either in a store that
  imported the discovery and then its deletion record; if it answers finished
  while a reader blocks the checkpoint; or if another discovery's metadata or
  notices go.

## Verification

Runs on `main` today:

```sh
uv run python -m pytest -q tests/analysis tests/maintenance tests/retention tests/privacy/test_learning.py tests/storage/test_learning.py tests/storage/test_learning_lineage.py tests/cli/test_learning.py tests/application/test_learning.py tests/promotion/test_lifecycle.py::test_deleted_supporting_data_invalidates_active_policy tests/privacy/test_round41_learning.py::test_report_sensitive_map_key_rejects_before_persistence --deselect tests/application/test_learning.py::test_installed_discovery_host_tasks_reports_analysis_and_entered_denials
```

Deliverables (the verifier commands are `learn.yml` steps):

```sh
uv run python -m pytest -q tests/privacy/test_shared_records.py tests/maintenance/test_lifecycle_faults.py tests/storage/test_wal_erasure.py tests/application/test_learning_limits.py tests/storage/test_discovery_erasure.py
uv run python -m pytest -q tests/verification/test_learn_phase.py
uv run python scripts/verify_learn_phase.py --local-only --agent-harness .host/companion
uv run python scripts/verify_learn_phase.py --reduce-only --agent-harness .host/companion
gh workflow run learn.yml --repo Consiliency/jevdrill --ref main -f companion_ref=<40-hex commit SHA>
```

The extras command, from the companion's `phase-loop-runtime` (deliverable;
the Windows files only on Windows):

```sh
<companion python> -m pytest -q tests/test_windows_locking.py tests/test_launcher_liveness.py tests/test_windows_processes.py tests/test_windows_storage.py --junitxml=<temporary>/extras.xml
```

Effective `automation.suite_command`: `uv run python scripts/verify_learn_phase.py --agent-harness .host/companion` (deliverable; a missing companion fails closed).

## The verifier

**It must check:** every control the clause tables name, by id and exact
count, on each platform where it runs; the installed control's pass and
witness; the inherited HOST receipts, by the HOST verifier; three native
receipts from one run, each naming its runner, command, platform, versions and
result; the companion at the pinned commit, clean, and the jevdrill checkout unchanged after its code ran; the extras
against each platform's list; module provenance; the coverage record and a
`no_spec_delta` closeout; each part's time recorded: HOST's call
within its two bounds, LEARN's part within 600 seconds;
flagging proof over five minutes; a malformed receipt reported, not raised. A
clause of EC-LEARN-1 to 5 that is not covered is reported so, never as passed,
and blocks IF-0-LEARN-1. HOST clauses are not covered today
(`evidence/HOST/coverage.json:54`), so the inherited HOST part would not produce
IF-0-HOST-1; while that holds, IF-0-LEARN-1 is not produced.

**It reads** the jevdrill checkout and the companion checkout at the pinned
commit. **It writes** `evidence/LEARN/platforms/` and
`evidence/LEARN/verification.json`, ignored by git. A verdict is the CI
artifact of the run that made it and is never committed.

**Declared changes to the held instrument:**

1. The reduce job gets "Require successful native jobs" as in `route.yml`;
   ignore rules for every path the verifier writes; the verdict is uploaded
   only when the reduction ran. Reason: Consiliency/jevdrill#74.
2. `learn.yml` as J1, with pinned actions and `workflow_dispatch`; the dotfiles
   checkout and the copy into it go. Reason: J1; that repository is private.
3. Receipts name repository, commit and a clean checkout; the reducer rejects
   a foreign commit. Reason: the extras and installed control must run at the
   pinned commit.
4. `test_learn_phase.py` builds receipts from the verifiers' constants and
   reads no committed receipt, list or verdict. Reason: those October files are
   not restored.
5. In `test_route_phase.py`, `learn` returns to
   `test_native_download_excludes_prior_reduction_reports` and joins
   `test_reduction_runs_only_after_every_native_job_succeeded`. Reason: both
   were cut while `learn.yml` was not on `main`.
6. `CONTROLS` and `evidence/LEARN/coverage.json` become the tables'
   controls, a parametrized one whole with its count (`[4]` and `[6]` where the
   tag named one and three cases), and record the clause not covered. Reason:
   the verdict binds the rows; Consiliency/jevdrill#71.
7. Same-run receipts only; any other is a diagnostic, never uploaded.
   Reason: Consiliency/jevdrill#73.
8. Native jobs collect and validate receipts without the lists and still fail
   on a native error; the reduction reports a missing list in a verdict that
   produces no gate. The reader takes SL-5's lists (repository, commit,
   platform, unique ids), not the tag's receipt-shaped files. Reason: the tag
   reads a list unguarded even in `--local-only`, so the first run's native
   jobs would fail after collecting.
9. IF-0-LEARN-1 also requires the inherited HOST reduction without error, its
   not-covered rule included. Reason: LEARN consumes IF-0-HOST-1.
10. Module provenance adds `src/jevdrill/integrations/archive.py`. Reason: it
    holds the lock and encryption of EC-LEARN-2 and 3.
11. The spec-delta record is re-made in the roadmap's words. Reason: the tag's
    names paths the roadmap does not.
12. As HOST's change 17: one unmodified HOST call, all else LEARN's part in
    LEARN's own commands, no test in two. Reason: `host.yml` run 45279806415,
    638.98 seconds on macOS.

## Acceptance Criteria

- [ ] EC-LEARN-1, EC-LEARN-2, EC-LEARN-3, EC-LEARN-4, EC-LEARN-5 — by the
  controls and falsifiers of the clause tables, reduced by SL-4's verifier from SL-5's run.

## This plan may not claim

- Any criterion verified or gate produced; IF-0-LEARN-1 before HOST evidence
  exists (`specs/phase-plans-v1.md:350`).
- Anything on the strength of the October reports, receipts or plans.
- That hosted runners can run the host integration, or that it is accepted.
- Proof against a real OS key store or an installed scheduler.
- That native synthetic HOST receipts supply empirical quality floors, guidance
  effectiveness or promotion evidence; they establish software conformance only.
- A causal, whole-skill or cross-domain claim.
- That a decline that starts no run is visible to learning.
- That "retain" is shown except as a refusal to replace an operator-set model.
- That LEARN evidence informs later discovery or task selection.
- That a shared record cannot be linked by a condition or value it still
  carries, such as its domains, guidance choices, context fields, policy
  revision, configuration digests or exact measurements; by a keyed value, which
  within one requester's view still links every observation sharing it; or by
  values stored before SL-1 or SL-7.
- That an export or backup is metadata only: it carries retained raw task,
  output and context content.
- That import or restore checks the text it writes back.
- That a measurement's text is checked for more than credential-like material.
- That a deleted discovery's item identities, as references or unsalted digests
  a catalog holder can map back, are gone from the decisions and retries of
  tasks routed with it or from notices copied into decisions, or that request
  text such a task supplied is gone: those records go when their task is
  deleted.
- Ratified review, publication, adoption or release readiness.

## Attached backlog

| Item | Disposition |
| --- | --- |
| Consiliency/jevdrill#86 (shared-record fingerprint) | Fix lane, SL-1, by the owner's decision; fix lane, SL-7, for `discovery_revisions` |
| Consiliency/jevdrill#21, #45 (both contradict EC-LEARN-3), #46, #52 | Fix lanes, SL-2 |
| Consiliency/jevdrill#125 | Fix lane, SL-8 |
| Consiliency/jevdrill#128, #139 | Fix lane, SL-8 |
| Consiliency/jevdrill#138, #TBD-METADATA, #21 | Fix lane, SL-9 |
| Consiliency/jevdrill#53, #58 (recovery and maintenance as ratified) | Verified as built by SL-3's controls; stated limits; the issues stay open as records |
| Consiliency/jevdrill#74 for `learn.yml`, and the changes ruled earlier for this cut (declared changes 1 to 5) | Fix lane, SL-4 |
| The held spec paragraph | Plan text and a "may not claim" line |
| The deselected installed test; LEARN coverage and spec-delta records; the expected-test lists | Run and re-made, SL-4 and SL-5 |
| ROUTE verifier not reopened except for a defect the LEARN verifier exposes; the deadline-failure rule | Stated limits, standing |

## Owner inputs

- **Who takes the host integration to a merged state**, as in the HOST plan.
  Without it only SL-1 to SL-3 and SL-7 to SL-9 can run.
- **Closing the LEARN gate**, including whether generated scheduler
  configuration and simulated key-store states satisfy EC-LEARN-2 and 3 under
  `specs/phase-plans-v1.md:354`, and what to do about each clause not covered,
  which blocks the verifier's gate:
  - EC-LEARN-5, "comparable evidence can inform later discovery and task
    selection": no path on `main` for either half. For selection the candidate
    fields exist and nothing fills them from analysis; for discovery a contract
    change would be needed, which is the owner's.
- **The options not chosen** in Consiliency/jevdrill#53 and #58: each changes
  the ratified contract.
- **Making a decline visible to learning**, as in the HOST plan.

## Execution Notes

Execute serially, one writer per lane; each lane's scope is fixed before it is
cut and reviewed as this plan was. SL-1 owns any storage migration this plan needs. No edit to `specs/phase-plans-v1.md`,
`docs/sanitization-contract.md`, `plans/manifest.json` or
`scripts/verify_route_phase.py` beyond the backlog's standing limits. Tests use
synthetic stores and keys only. A control entered through `Application` or the
command line reaches the default key provider (`maintenance.py:28`), in a child
process for the command line; its lane keeps it off every OS key store and says
how.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`; decision: `no_spec_delta`
- target surfaces: learning/retention contracts; evidence paths: `evidence/LEARN/spec-delta.json`
- redaction_posture: `metadata_only`; missing/malformed evidence: `blocker_class=contract_bug`, non-human repair

No roadmap text is amended by this plan.
