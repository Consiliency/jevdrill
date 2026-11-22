---
phase_loop_plan_version: 1
phase: PREPARE
roadmap: specs/phase-plans-v1.md
roadmap_sha256: 4ecbf27188b634d6ea5346cd67d61ab36d50d3ad0416a9a6d0d2602bb2698ab8
---

# PREPARE: Release preparation and governance readiness

> Review status: draft written by Claude Opus 5.5. Board: a Fable 5.2 president
> with three seats (correctness; security and privacy; alternate vendor).
> Rounds: none yet. Pull request: not yet opened.
> This is a reviewed plan. It verifies no criterion.

## Context

This plan revises PREPARE against the amended roadmap, EC-PREPARE-1 to 4 and
IF-0-PREPARE-1. It starts from `main`'s plan of three criteria; its pin,
banner, carried authority, worktree, chosen package number and prepared
workflow do not survive.

Nothing here builds a release, publishes, tags, uploads, signs, dispatches or adopts anything, opens a holdout, calls a provider, reads a credential, spends money, requests a host run, reports ratification or closes a gate.

Everything below is a deliverable. "Dispatch" here means dispatching a
release, which nothing here does; a workflow's manual trigger is named by its
keyword, `workflow_dispatch`.

Length exception: every clause is mapped to code, control, falsifier and
evidence kind.

## State of `main` at `1fad80695`

**Of PREPARE, nothing.** No `tests/release/`, `scripts/verify_prepare*`,
PREPARE workflow, `CHANGELOG.md`, `evidence/PREPARE/` or
`evidence/decision-coverage.json`. Nothing of PREPARE is held at
the tag but this plan's starting text.

**What PREPARE builds on.**

| What | Where it landed |
| --- | --- |
| `tests/contracts/test_package.py` (the wheel routes once outside the checkout) | CONTRACT foundation; changed in Consiliency/jevdrill#54 |
| `evidence/CONTRACT/coverage.json` and `scripts/check_contract_coverage.py` | CONTRACT foundation |
| Storage and its migrations (`src/jevdrill/storage.py`) | Consiliency/jevdrill#18 |
| `maintenance.py` and the recovery commands | Consiliency/jevdrill#44, #54 |
| The ROUTE verifier and `route.yml` | Consiliency/jevdrill#66 |

The CONTRACT and ROUTE verifiers pass on `main` in CI
(`docs/roadmap-status.md:7`); neither gate is closed. The HOST, LEARN and
EXPERIMENT verifiers are not on `main`.

## External Inputs

- Host integration, inspected: as in the HOST plan (draft
  Consiliency/agent-harness#2071 at `784d1595a08f42519862ae5f9336f20186d83c4b`,
  unchanged on 2026-11-22). Its roadmap reader there is
  `phase_loop_runtime/roadmap_lint.py` (`_extract_phases`); R1 does not
  require it.
- Governed-pipeline (`specs/phase-plans-v1.md:59`). Its repository is not
  public (an unauthenticated read answers 404, 2026-11-22), so the revision
  named at `specs/jevdrill-current-state.md:65` (`15f2d40ec6d…`) and the
  documents at `:67-70` were not inspected. Public: the npm package
  `@consiliency/pipeline-runtime` 0.4.0 (integrity
  `sha512-B4ACGTvw5ajQTjztSK/e+k6uMbi9p0owJ42VX7UW5I6KPOKj/yfdemyysZsDRvtPmJs3wcvozeCVhug6/5LsBw==`),
  whose metadata names that repository's `packages/pipeline-runtime`, records
  no source commit and declares no license. Its file list, read and not run,
  shows a roadmap HTML producer (`src/canonical-html/produce-phase-roadmap.mjs`)
  and canonical-HTML lint modules, and none of those documents. Whether it
  holds the source-role and representation checks EC-PREPARE-2 needs is not
  established.
- JEV Drill on Python 3.14 (`pyproject.toml:9`); BAML `baml-language-0.20.1`
  and `baml-bridge==0.20.1`.
- Read inputs: `main`, the draft and the package's public metadata and file
  list; nothing else.

## Interface Freeze Gates

- [ ] IF-0-PREPARE-1 — Release evidence, package inputs and canonicalization
  readiness (`specs/phase-plans-v1.md:82`).
- Consumed, each from its reducer: IF-0-CONTRACT-1 from
  `scripts/verify_contract_phase.py` (status at `:129`) and IF-0-ROUTE-1 from
  `scripts/verify_route_phase.py` (status at `:695`), on `main`; neither
  verdict names a gate. IF-0-HOST-1, IF-0-LEARN-1 and IF-0-EXPERIMENT-1 as
  their plans define them.

## Criteria, clause by clause

Naming and evidence kinds as in the LEARN plan. Sources are under
`src/jevdrill/` unless a path says otherwise; new tests are under
`tests/release/` (`specs/phase-plans-v1.md:325`). Nothing below is verified.

**EC-PREPARE-1** (`specs/phase-plans-v1.md:310`)

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Package installation on supported platforms | Command `pyproject.toml:12-13`; wheel `:25-26` | main `tests/contracts/test_package.py::test_installed_wheel_cli_outside_checkout` (one route; dependencies from the checkout's environment, `:77`); D new, SL-2: the wheel and its locked dependencies in an environment that cannot import the checkout | A module missing from the wheel, the command absent from the environment, or the checkout's `src/` imported | native CI run |
| Upgrade | `user_version` above 4 refused, `storage.py:597-599`; set to 4 at `:723` | D new, SL-2: a store written by the wheel of an earlier `main` commit, named by full SHA, opened by the new wheel | A record lost or changed, or the open failing | native CI run |
| Migrations | As above; SL-1's migration | main `tests/storage/test_storage.py::test_migration_failure_is_atomic` (a failed migration leaves `user_version` 0 and the rows); D new, SL-2: the migrating process killed midway, then reopened | A partly migrated store after a failure or a kill | native CI run |
| Recovery | `maintenance.py:366-439` | The LEARN plan's EC-LEARN-3 rows "Restoration" and "Inspectable export, import and backup …"; D new, SL-2, through the installed command: a backup imported into a fresh store elsewhere keeps its deletion records; the earlier wheel refuses the upgraded store, unchanged, and reads the copy taken before the upgrade | Deleted content back after import; an older wheel that opens or alters a newer store | native CI run |
| Full acceptance suites pass on supported platforms | The five verifiers | D new, SL-5: in one run, on each platform, the five verifiers' collections and `unit.yml`'s test command; their reductions without error | A platform missing, a failure, or a verifier not run | native CI run; needs the host integration; needs a container |
| Version, changelog, docs and release inputs agree | `pyproject.toml:7`; `tests/contracts/test_package.py:37` fixes the wheel's metadata directory | D new, SL-2: the `version` field, the wheel and sdist names, the top entry of `CHANGELOG.md` and the runbook's install command agree; SL-5's reducer adds the input manifest. README links: not covered: needs an owner input (Consiliency/jevdrill#81) | Any one differing | native CI run |
| "Thresholds are frozen before holdout testing" | For policies, exposure before freezing is refused (`evaluation.py:320-322`) | Not covered: needs an owner input; the release evaluation has no lane | — | needs an owner input |
| "Unmet quality floors or insufficient evidence prevent promotion claims" | For policies, `evaluation.py:256`, `:266` | Policies: the EXPERIMENT plan's EC-EXPERIMENT-3 rows. The release: not covered: needs an owner input | — | needs an owner input |

**EC-PREPARE-2** (`specs/phase-plans-v1.md:311`)

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Every accepted decision and unchanged draft requirement maps to implemented evidence or explicit deferred scope | `evidence/CONTRACT/coverage.json`: 84 decisions and 146 draft blocks, none claimed as implemented | D new, SL-3: `test_decision_coverage.py` on `evidence/decision-coverage.json`; reducer: each `implemented` entry's controls passed in the run. A deferral that changes public scope: not covered: needs an owner input | An entry missing or twice; a control that does not exist or did not pass; a deferral without scope; JD-043 or JD-079 mapped to its original text | native CI run; needs an owner input |
| Brownfield dry-run artifacts preserve source roles | None; the role definitions are not public | Not covered until SL-4's scope names a public source; then D new, SL-4 | A role swapped or dropped | — |
| And YAML/BAML authority | `baml_src/` (`docs/contract-decisions.md:15`); `docs/vocabulary.yaml` (`specs/jevdrill-design-input.md:88`) | D new, SL-4: the dry-run bundle names both as authorities and every generated file as derived | A swapped authority, or a generated file as authority | synthetic; native CI run |
| HTML-to-harness representation checks preserve aliases, EC IDs, gates and dependencies | None | Not covered until SL-4's scope names a public HTML producer and HOST's pinned commit carries the harness reader; then D new, SL-4: the roadmap rendered to HTML, read back by the harness, equal to `specs/phase-plans-v1.md` in aliases, EC and IF ids and edges | A renamed alias, a dropped id or gate, or a missing edge | synthetic; needs the host integration |
| Adoption remains a separate action | — | D new, SL-4, SL-5: the dry run's file check; the workflow and option checks (under "The verifier") | A run that writes `.pipeline/`, another repository, or any path outside its fixtures and record | native CI run |

**EC-PREPARE-3** (`specs/phase-plans-v1.md:312`)

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Operational evidence reviewable | — | D new, SL-5: receipts naming runner, command, platform, versions and result, and the verdict, kept as the run's artifacts | A receipt missing a field; a verdict without its run's receipts | native CI run |
| Recovery instructions reviewable | — | D new, SL-2: `docs/release-runbook.md`; `test_runbook.py`: every command in its command blocks is one SL-2's controls run, and install, upgrade, migration, recovery and rollback each have one | A runbook command no control runs, or a step absent | native CI run |
| A "release-dispatch input manifest" reviewable | — | D new, SL-5: `evidence/PREPARE/release-inputs.json`, made in the run: commit; the `version` field as found; wheel and sdist digests; lock, schema and vocabulary digests; the companion's repository and commit; the run's receipt and verdict references; `publication_performed: false`, `canonical_adoption: false`. The reducer recomputes each digest | A digest unlike the run's build or checkout, a field missing, a flag true, or a field naming a registry, account or signing service | native CI run |
| "No publishing occurs" | — | D new, SL-5: `test_prepare_workflow.py` | Under "The verifier" | native CI run |
| "Ratification is reported only with required cross-vendor ablation evidence for Sol-authored plans" | — | D new, SL-5: no output of this plan's scripts has a ratification field or claim. The evidence: not covered: needs an owner input | Any output reporting ratification | native CI run; needs an owner input |

**EC-PREPARE-4** (`specs/phase-plans-v1.md:313`)

| Clause | Implementation | Control | Falsifier | Evidence |
| --- | --- | --- | --- | --- |
| Supported-platform installed acceptance covers objective → discovery → harness decomposition → per-task configuration → observations → analysis with linked evidence | The HOST plan's EC-HOST-4 rows; the LEARN plan's EC-LEARN-5 first row | Their installed controls, run by SL-5 with the wheel's environment as `JEVDRILL_TEST_PYTHON` and `JEVDRILL_TEST_CLI`, on Linux, macOS and Windows | A step missing from the entered trace or witness, a broken link, a platform missing, or the flow run from the checkout's environment | native CI run; needs the host integration |
| Verify every added drill-down criterion against the amended roadmap and current source | The table below | D new, SL-5: the reduction requires each criterion's verdict, from its reducer, in the same run | EC-PREPARE-4 passing with one missing, failing, not covered or of another commit | native CI run; needs the host integration; needs a container; needs an owner input |
| Missing progressive discovery blocks full release acceptance | EC-ROUTE-5 to 7 | The same reduction; the HOST row's entered-trace check | An installed flow without `discover` in its trace passes | needs the host integration |
| "The internal V0 checkpoint and standalone model benchmarks do not waive it" | — | D new, SL-5: the verifier reads no such record; a reducer test with one present and an installed-flow receipt absent | That reduction passes | native CI run |
| Preserve holdout isolation | `evaluation.py:96-97`, `:314-315` | The EXPERIMENT plan's row "The release holdout remains untouched"; the PREPARE verifier reads no dataset | A dataset among the verifier's inputs | synthetic; native CI run |
| Separate publication authority | — | As "No publishing occurs" | As there | native CI run |

**The added criteria.** PREPARE re-verifies none; its control is the
reduction above.

| Criterion | Verified or planned | Left not covered there |
| --- | --- | --- |
| EC-ROUTE-5 to 7 | ROUTE verifier on `main` (`scripts/verify_route_phase.py:70-85`), passing in `route.yml` | None reported; the evidence is synthetic, and real decomposition is HOST's (`docs/route-readiness.md:73-77`) |
| EC-HOST-4 | HOST plan, EC-HOST-4 rows | A launch that keeps the harness's current model |
| EC-LEARN-5 | LEARN plan, EC-LEARN-5 rows | "Comparable evidence can inform later discovery and task selection" |
| EC-EXPERIMENT-4 | EXPERIMENT plan, its EC-EXPERIMENT-4 table | Every clause: needs an owner input |

**Gates**

| Item | Control | Falsifier | Evidence |
| --- | --- | --- | --- |
| PREPARE reducer rejects invalid receipts (plan-level) | D new `test_prepare_phase.py::test_reducer_rejects_invalid_receipts` [one case per rejection, each asserting its own error], `::test_reducer_accepts_valid_receipts` | A fault that passes or does not raise its own error; a valid receipt rejected | native CI run |
| IF-0-PREPARE-1 | Reducer: every clause covered, its controls passed where they run, receipts of one run, the five consumed reductions without error | A gate produced with a clause not covered, a platform or job missing, receipts of different runs, or a consumed reduction failing | native CI run, no model called; needs the host integration; needs a container |

## Readings and points settled

- **PREPARE's decision range** (`specs/phase-plans-v1.md:317`), each first
  sentence read against `main`. Agrees: JD-047 to JD-050, JD-054 to JD-059,
  JD-062, JD-063. Parts not built, for SL-3 to map: JD-007's three-platform
  distribution; JD-046's acceptance of the later deliveries (the HOST to
  EXPERIMENT verifiers); JD-051's release gate; JD-052, JD-053 and
  JD-061, whose dry run is SL-4's; JD-080's values (its rule is
  `evaluation.py:304-313`). JD-060's first sentence records JD-043's default
  as history; `main` has it off (`settings.py:23-25`), as the JD-043
  paragraph of `docs/contract-decisions.md` (`:52`) decides, and that
  paragraph does not name JD-060. Whether it governs JD-060 is an owner
  input.
- **Parts not built in other ranges:** JD-038 and JD-042
  (Consiliency/jevdrill#97); JD-036, JD-074 and JD-075
  (Consiliency/jevdrill#103). SL-3 maps each and decides no deferral.
- **Owner decisions on `main`:** the JD-043 and JD-079 paragraphs of
  `docs/contract-decisions.md`, "Changes to accepted decisions", the second as
  corrected by Consiliency/jevdrill#101.
- **The installed flow** is HOST's and LEARN's, named by their rows. PREPARE
  adds the same flow from the wheel, in an environment holding only it and the
  locked dependencies, on three platforms. Today the LEARN control hands on
  its own interpreter and the command beside it
  (`tests/application/test_learning.py:79-83`, `:315`).
- **Review evidence in public:** the four plan pull requests
  (Consiliency/jevdrill#89, #92, #98 and this plan's) and their bodies. This
  plan claims no ratification and cites no non-public record.
- **The release evaluation has no lane.** It needs a holdout and frozen
  thresholds. No release holdout exists; one is an owner prerequisite, and
  thresholds are frozen before it is opened.
- **Release dispatch** is the separate phase of `specs/phase-plans-v1.md:64`,
  by the owner's word; the input manifest is a file, not a workflow.
- **Stated limits from the roadmap:** "Windows unsigned-launcher
  compatibility and … thinking/final-answer separation remain disclosed
  limitations" (`specs/phase-plans-v1.md:37`). The runbook states both.
- **No request leaves the runner,** as the EXPERIMENT plan words it, except
  `uv` fetching packages for builds and installs, as
  `tests/contracts/test_package.py` does today. The earlier commit comes with
  the job's checkout; the installed flow keeps the host integration's loopback
  stand-in.
- **Consiliency/jevdrill#20** (two store files in one directory share
  `artifacts/<digest of the scope>`, `storage.py:1873-1874`): a fix lane, SL-1,
  ahead of the migration controls. Reason: the upgrade and rollback controls
  keep a store's earlier copy, and a copy in the same directory would share
  its artifacts.

## Cross-Repo Gate

This plan owns no path in `Consiliency/agent-harness`
(`specs/phase-plans-v1.md:192`) and pins nothing. The pin's conditions and
jevdrill's obligations are the HOST plan's "Cross-Repo Gate"; PREPARE uses
HOST's pinned commit, and `prepare.yml` follows J1 as that plan words it.

**Where the evidence comes from.** One `workflow_dispatch` run of
`prepare.yml` on hosted Linux, macOS and Windows runners, with EXPERIMENT's
runtime job on hosted Linux.

## Lane Index & Dependencies

- SL-1 — Artifact namespace; Depends on: (none); Blocks: SL-2; Parallel-safe: no
- SL-2 — Package, upgrade and recovery controls; Depends on: SL-1; Blocks: SL-5; Parallel-safe: no
- SL-3 — Decision map; Depends on: (none); Blocks: SL-5; Parallel-safe: no
- SL-4 — Dry run; Depends on: (none); Blocks: SL-5; Parallel-safe: no
- SL-5 — Verifier and workflow; Depends on: SL-2, SL-3, SL-4, EXPERIMENT's verifier lane on `main`; Blocks: SL-6; Parallel-safe: no
- SL-6 — Readiness doc; Depends on: SL-5 and one run; Blocks: (none); Parallel-safe: no

## Lanes

### SL-1 — Artifact namespace

- **Needs:** GitHub CI alone.
- **Owned files:** `src/jevdrill/storage.py` (`_artifact_directory` and the
  migration), `tests/storage/test_artifact_namespace.py` (new).
- **Delivers:** fix lane for Consiliency/jevdrill#20, by one of its two
  options, stated in the pull request, with the migration it needs. SL-1 owns
  every storage migration here. The control fails if deleting a task in
  one store removes another store's artifact, if a second store in one
  directory shares the first's artifacts, or if a store at `user_version` 4
  loses an artifact on migration.

### SL-2 — Package, upgrade and recovery controls

- **Needs:** GitHub CI alone.
- **Owned files:** `tests/release/test_package_upgrade.py`,
  `tests/release/test_recovery.py`, `tests/release/test_release_metadata.py`,
  `tests/release/test_runbook.py`, `CHANGELOG.md`, `docs/release-runbook.md`
  (all new); the `testpaths` line of `pyproject.toml`; the test and lint lines
  of `.github/workflows/unit.yml`.
- **Delivers:** the "D new, SL-2" controls, each run from a wheel built inside
  the test, in an environment it makes, through the installed command. The
  earlier wheel's commit is fixed in the test and fetched by its job's
  checkout. SL-2 is the one owner of release metadata
  (`specs/phase-plans-v1.md:317`): `CHANGELOG.md` records the `version` field
  as found, and nothing changes that field. It adds `tests/release` to
  `testpaths` (`pyproject.toml:30`) and to `unit.yml`'s commands; tests there
  that need more than `uv sync` run only in `prepare.yml`. The installed
  commands reach the default key provider (`maintenance.py:28`) in a child
  process; the lane keeps them off every OS key store and says how.

### SL-3 — Decision map

- **Needs:** GitHub CI alone.
- **Owned files:** `evidence/decision-coverage.json`,
  `tests/release/test_decision_coverage.py` (new).
- **Delivers:** one entry per entry of `evidence/CONTRACT/coverage.json`,
  with its source digest. Each `planned` one becomes `implemented`, naming its
  controls by id, or `deferred`, naming the scope and whether it changes
  public scope; `context` and `superseded` entries keep their status. The
  JD-043 and JD-079 entries cite their paragraphs; the parts named under
  "Readings" are entered as parts not built.

### SL-4 — Dry run

- **Needs:** a public governed-pipeline source for source roles and the HTML
  rendering, named by its digest in the lane's reviewed scope, and HOST's
  pinned commit for the harness reader; GitHub CI. Without them it delivers
  only the YAML/BAML authority row, which needs GitHub CI alone, and the two
  "not covered" rows stand.
- **Owned files:** `scripts/verify_prepare_dry_run.py`,
  `tests/release/test_dry_run.py` (new).
- **Delivers:** the script takes no path or other option, makes its own
  temporary fixtures, writes only there and its one record,
  `evidence/PREPARE/adoption-dry-run.json` (`specs/phase-plans-v1.md:339`),
  and removes the fixtures. The test copies the checkout, runs the script and
  fails on any other file changed or created, a swapped authority, or a
  dropped id or edge.

### SL-5 — Verifier and workflow

- **Needs:** EXPERIMENT's verifier lane on `main` (this verifier loads it,
  which loads LEARN's and HOST's), HOST's pinned commit; GitHub CI and a
  container.
- **Owned files:** `scripts/verify_prepare_phase.py`,
  `tests/release/test_prepare_phase.py`,
  `tests/release/test_prepare_workflow.py`, `.github/workflows/prepare.yml`
  (all new), `evidence/PREPARE/coverage.json`, `evidence/PREPARE/spec-delta.json`,
  the PREPARE lines of `.gitignore` and `tests/verification/test_route_phase.py`,
  and the interpreter choice of the installed test of
  `tests/application/test_learning.py` (`:315`), keeping its checks and
  witness.
- **Delivers:** the verifier and its tests, passing in CI; the workflow as
  under "The verifier", its reduce job needing every native and runtime job,
  "Require successful native jobs" as in `route.yml`. Its writer starts one run
  on `main` with the pinned SHA.

### SL-6 — Readiness doc

- **Needs:** SL-5's run, with its verdict artifact, if any.
- **Owned files:** `docs/release-readiness.md` (new).
- **Delivers:** the run linked, its verdict as that run's artifact or why it
  has none; the clauses not covered and the owner inputs.

## Verification

Runs on `main` today (the first line in `contracts.yml`'s environment):

```sh
uv run python -m pytest -q tests/contracts/test_package.py::test_installed_wheel_cli_outside_checkout
uv run python -m pytest -q tests/storage/test_storage.py::test_migration_failure_is_atomic
uv run python scripts/check_contract_coverage.py
```

Deliverables (the verifier commands are `prepare.yml` steps):

```sh
uv run python -m pytest -q tests/storage/test_artifact_namespace.py tests/release/test_package_upgrade.py tests/release/test_recovery.py tests/release/test_release_metadata.py tests/release/test_runbook.py tests/release/test_decision_coverage.py
uv run python -m pytest -q tests/release/test_dry_run.py tests/release/test_prepare_phase.py tests/release/test_prepare_workflow.py
uv run python scripts/verify_prepare_dry_run.py
uv run python scripts/verify_prepare_phase.py --local-only --agent-harness .host/companion
uv run python scripts/verify_prepare_phase.py --reduce-only --agent-harness .host/companion
gh workflow run prepare.yml --repo Consiliency/jevdrill --ref main -f companion_ref=<40-hex commit SHA>
```

Effective `automation.suite_command`: `uv run python scripts/verify_prepare_phase.py --agent-harness .host/companion` (deliverable; a missing companion fails closed).

## The verifier

**It must check,** under the three plans' verifier rules, the tables' controls
by id and exact count on each platform where they run; three native receipts
of one run, each naming runner, command, platform, versions and result; the
five consumed reductions, made in the same run; the installed flow from the
wheel's environment; the manifest's digests; the decision map against the
run's outcomes; the dry-run record; the coverage record and the closeout; each
collection within its own verifier's bound, flagging proof over five minutes;
a malformed receipt reported, not raised.

**One rule for this plan.** A clause whose only possible control is an
owner-set value, a holdout or a review the owner names is reported "not
covered: needs an owner input" and blocks IF-0-PREPARE-1 like any other.
IF-0-PREPARE-1 is not produced while any consumed gate would not be. Today
five HOST clauses and one LEARN clause are not covered, and the EXPERIMENT
verdict is `blocked` by design (the LEARN and EXPERIMENT plans, "The
verifier").

**What cannot happen.** Nothing this plan specifies can publish, dispatch or
adopt. `test_prepare_workflow.py` fails if `prepare.yml` has a trigger other
than `workflow_dispatch`, an input other than `companion_ref`, a permission
other than `contents: read`, any `secrets.` reference, a login or registry
step, a step that publishes, uploads to a registry, tags, signs or pushes, or
a checkout without `persist-credentials: false`. `test_prepare_phase.py` fails
if `verify_prepare_phase.py` accepts an option beyond `--local-only`,
`--reduce-only` and `--agent-harness`, or `verify_prepare_dry_run.py` any
option. The wheel and sdist are built inside the run and kept in none of its
artifacts; the manifest records their digests.

**It reads** the jevdrill checkout, the companion at HOST's pinned commit,
the receipts of its own run and SL-4's named package. It reads no committed
verdict (`evidence/CONTRACT/verification.json` included), no dataset, no V0
or benchmark record and no review record. **It writes**
`evidence/PREPARE/platforms/`, `verification.json`, `release-inputs.json` and
`adoption-dry-run.json`, ignored by git, temporary directories, and what each
verifier it runs writes, as that verifier's plan states. A verdict is the CI
artifact of the run that made it and is never committed.

**Declared changes:** none. No PREPARE instrument exists; every script, test
and workflow named here is new.

## Acceptance Criteria

- [ ] EC-PREPARE-1, EC-PREPARE-2, EC-PREPARE-3, EC-PREPARE-4 — by the
  controls and falsifiers of the clause tables, reduced by SL-5's verifier
  from one run.

## This plan may not claim

- Any criterion verified or gate produced; any upstream gate as produced.
- Release readiness, or that any version, date or name is chosen.
- That a holdout exists or any result on one; any threshold or floor.
- Ratification of any review, the plan reviews included.
- Publication, dispatch or adoption, or authority for any of them.
- That the governed-pipeline package holds the checks EC-PREPARE-2 needs, or
  that hosted runners can run the host integration or the container.
- That the installed flow shows more than its HOST and LEARN rows show.
- That a deferral is decided, or that JD-060 is settled.
- Anything on the strength of the September or October records.

## Attached backlog

| Item | Disposition |
| --- | --- |
| Consiliency/jevdrill#20 (shared artifact directory) | Fix lane, SL-1 |
| Consiliency/jevdrill#81 (README links into `research/`) | Owner input; the README-links clause stays not covered |
| The release holdout | Owner input; the release evaluation has no lane |
| Consiliency/jevdrill#97, #103 | Parts not built, mapped by SL-3 |
| ROUTE verifier not reopened except for a defect this verifier exposes; the deadline-failure rule | Stated limits, standing |

## Owner inputs

None is asked here; each blocks what it names.

- **Who takes the host integration to a merged state**, as in the HOST plan.
  Without it only SL-1 to SL-3, and SL-4's authority row, can run.
- **The EXPERIMENT plan's owner inputs.** Without them neither
  IF-0-EXPERIMENT-1 nor IF-0-PREPARE-1 is produced.
- **A private held-out set and frozen thresholds.** Without them the release
  evaluation has no lane and EC-PREPARE-1's last two clauses stay not
  covered.
- **Each deferral that changes public scope.** Without a decision its entry
  blocks EC-PREPARE-2.
- **Whether the JD-043 paragraph governs JD-060.** Without it SL-3 records
  JD-060 as open.
- **The README's links into `research/`** (Consiliency/jevdrill#81).
  Without it the README-links clause stays not covered.
- **The review EC-PREPARE-3 requires for ratification.** Without it no
  ratification is reported.
- **Any change to the `version` field, and every act of publication,
  dispatch or adoption.** Without them none happens.
- **Closing the PREPARE gate**, including each clause not covered.

## Execution Notes

Execute serially, one writer per lane; each lane's scope is fixed before it is
cut and reviewed as this plan was. GitHub-CI-only lanes come first: SL-1,
SL-2, SL-3. No edit to `specs/phase-plans-v1.md`, `plans/manifest.json` or
`scripts/verify_route_phase.py` beyond the backlog's standing limits. Tests
use synthetic stores only. Nothing writes `.pipeline/`, a sibling
repository, a registry or a mirror.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`; decision: `governed_pipeline_refresh` (metadata-only deferral)
- target surfaces: future canonical source registry and managed mirrors; evidence paths: `evidence/PREPARE/spec-delta.json`, `evidence/PREPARE/adoption-dry-run.json`
- redaction_posture: `metadata_only`; missing/malformed evidence: `blocker_class=contract_bug`, non-human repair. No `.pipeline/` writes authorized by this policy.

`evidence/PREPARE/adoption-dry-run.json` is written inside the run and kept as
its artifact, not committed. No roadmap text is amended by this plan.
