# Phase roadmap v1

## Context

JEV Drill selects a model, native effort, and optional guidance that meet task requirements at the lowest estimated token cost. This roadmap turns the [accepted decisions](jevdrill-design-input.md) into implementation boundaries. Read the preserved [product draft](../docs/jevdrill-spec.md), [reuse assessment](jevdrill-current-state.md), [implementation proposal](jevdrill-implementation-proposal.md), and [BAML proof](../research/baml-proof/README.md) alongside it. Accepted corrections take precedence over older draft wording.

At original intake, research catalog helpers and 55 research tests existed but the application did not. The original BAML proof demonstrated generation, Python interoperability, schema export, mocks, timeout behavior and one live call; its validation was too permissive for public contracts. These are historical intake findings, not current implementation status.

Use `codex-plan-phase specs/phase-plans-v1.md <ALIAS>` to create each detailed plan. Checkboxes are requirements, not the execution ledger.

## Drill-down coverage correction

The original draft §11 explicitly requires progressive navigation. Earlier ROUTE criteria covered catalog filtering and configuration selection without requiring the navigation loop itself. CONTRACT's coverage obligation did not prevent this behavior-level gap. The [drill-down implementation map](../docs/drill-roadmap-map.md) distinguishes existing code from missing behavior and supplies falsifiers for the added criteria.

This amendment preserves phase IDs, dependencies and historical evidence. EC-ROUTE-5–7, EC-HOST-4, EC-LEARN-5, EC-EXPERIMENT-4 and EC-PREPARE-4 are unproven. Existing ROUTE-through-PREPARE plans require revision before execution against this scope; changing their roadmap hash alone is insufficient. Replan ROUTE first, applying CONTRACT compatibility checks to added interfaces. Earlier gate reports do not establish the amended gates. No live-run allowance, policy authority or release scope changes.

Length exception: this roadmap exceeds 3,000 words to preserve existing acceptance obligations and stable IDs while adding the missing behavior. Detailed traces and implementation mapping live in the linked document.

## Approved internal V0 checkpoint

On October 1, 2026 the owner approved a Linux-first internal V0 focused on
routing and reporting under JD-046 stage 1. The bounded deployment plan is
[`detailed-v0-linux-20261001.md`](../plans/detailed-v0-linux-20261001.md).
This checkpoint consumes CONTRACT, ROUTE and scoped HOST proof and may run
before complete EXPERIMENT and PREPARE acceptance. It does not close their gates.
It proves a bounded routing/reporting checkpoint, not complete skill discovery.

V0 requires an isolated installed package, fresh Linux software verification,
one actual model task through the harness bridge, durable reporting/replay,
upgrade/recovery proof and explicit rollback instructions. Automatic learning,
background experiments and policy promotion remain disabled. Model prices and
measurements that are unavailable remain unknown; no savings or general quality
claims are authorized by a smoke test.

The full first public release still requires Linux, macOS and Windows, all six
phase gates and PREPARE evidence. Windows unsigned-launcher compatibility and
Gemma thinking/final-answer separation remain disclosed limitations. No purchase,
service restart, package publication, canonical adoption or fleet default change
is part of this internal checkpoint.

## Architecture North Star

`agent-harness adapter → JSON CLI → application → pure routing/costing/evaluation rules`

Product flow: objective → progressive guidance discovery → guidance returned to harness → harness decomposes work → configuration selection for each task → execution observations → comparable evidence. Discovery navigates domain → specialty → task → candidate descriptions → selected instructions, with exact-match shortcuts and bounded alternative paths. Drill owns questions, state transitions and stopping; JEV supplies typed judgments. The harness owns decomposition and execution. One skill can lead to several tasks with different models, efforts or execution routes.

Application wires storage, inventory, context, telemetry and BAML/JEV integrations. BAML authors contracts; generated types and strict derived validation enforce boundaries. YAML owns vocabulary. SQLite and indexed artifacts retain evidence. JEV Drill owns analysis and experiments; the harness owns task execution and authorization. Follow the proposal's acyclic import graph, amended explicitly when implementation evidence requires it.

## Assumptions

- Git home is the user-authorized public `Consiliency/jevdrill` repository. Local `main` and `origin` are initialized; commits, publishing workspace content and canonical adoption remain separate actions.
- Python support and packaging choices freeze in CONTRACT; Linux, macOS and Windows are required for release.
- Initial execution routes come from verified agent-harness capabilities. JEV's routing connection is separate.
- Product choices are settled; technical gaps block their affected interfaces, not another broad interview.

## External Inputs

- Initial BAML toolchain pin: `baml-language-0.20.1`; bridge `baml-bridge==0.20.1`. Archive checksum and tested dependencies are in the proof. Pin changes require recorded reasons and repeated compatibility checks.
- Agent-harness and governed-pipeline are external integration inputs. Detailed plans must record inspected versions and supported interfaces; prior inspection is supporting evidence, not a future-output commit requirement.

## Non-Goals

- Automatic objective recommendation, additional execution-provider adapters, unrestricted guidance composition, or a persistent routing service.
- Publishing packages, triggering external releases, automatic canonical adoption, or changing unrelated research behavior. Add a separate release-dispatch phase if dispatch is later requested.

## Cross-Cutting Principles

- Preserve JD-001–JD-082 and unchanged draft requirements with explicit coverage or deferral; no silent supersession. Readiness, authorization, acceptance and preference remain distinct.
- Raw token cost remains available; optional subscription adjustment is separate. Missing values remain unknown. Quality/privacy/permission gates cannot be traded away implicitly.
- Versions, identities, sources and objective definitions accompany evidence. Replay uses recorded judgments; another JEV call is new evidence.
- Exclusions apply to queues, retained context and experiment inputs. No credentials in fixtures, evidence or handoffs.
- Each detailed plan must reference EC IDs, declare owned files, provide machine-checkable commands and an effective `automation.suite_command`. Checks aggregate failures where practical.
- Every phase writes `spec_delta_closeout.v1` evidence; missing/malformed evidence routes to non-human `blocker_class=contract_bug`. Policies below are metadata-only routing, not canonical write authorization.

## Top Interface-Freeze Gates

- IF-0-CONTRACT-1 — Strict generated contracts, vocabulary/import rules, metric definitions and evaluation protocol.
- IF-0-ROUTE-1 — Bounded progressive discovery and task configuration selection, with durable state, reporting and replay.
- IF-0-HOST-1 — Guidance handoff, harness-owned decomposition, per-task routing, reporting queue and cross-platform conformance.
- IF-0-LEARN-1 — Comparable evidence updates, maintenance and retention lifecycle.
- IF-0-EXPERIMENT-1 — Authorized comparisons and objective-scoped promotion/rollback.
- IF-0-PREPARE-1 — Release evidence, package inputs and canonicalization readiness.

## Phases

### Phase 1 — Contract and toolchain foundation (CONTRACT)

**Objective**

Close the BAML proof gaps and freeze shared interfaces before implementation fans out.

**Exit criteria**

- [ ] EC-CONTRACT-1 — Generate the common request envelope, route requests (including prior decision/run links for retries), five response variants, capability-mismatch diagnostics, immutable plan/run/event/experiment/settings contracts and portable schemas from BAML; negative fixtures reject unknown fields, scalar coercion (including numeric strings), unsupported versions, invalid status combinations and missing required-nullable fields. Distinguish explicitly omittable fields from required nullable fields. Namespaced extensions cannot alter execution.
- [ ] EC-CONTRACT-2 — Prove reproducible generation, Python and one non-Python fixture consumer, aliases/enums, cancellation/error mapping and sanitized usage events. Exported schemas and Python validation must produce identical accept/reject results on shared positive/negative fixtures run by the non-Python consumer; rules schemas cannot express require named validators. Run these fixtures with the pinned bridge and generated package on Linux/macOS/Windows for every frozen Python version; record evidence in `evidence/CONTRACT/verification.json`. Failures require a recorded pin change or blocking open question. Resolve runtime-coupled imports explicitly without handwritten duplicate field catalogs.
- [ ] EC-CONTRACT-3 — Vocabulary and import checks reject invalid identifiers, aliases, ownership, cycles and stale outputs while permitting documented external/historical exceptions. Freeze Python versions, package commands, transport deadlines, exit codes, cancellation, compatibility rules (major versions, adapter version negotiation, deprecated names), idempotency canonicalization and event/experiment transitions. Later contract changes add shared fixtures and repeat parity/platform checks.
- [ ] EC-CONTRACT-4 — Define versioned quality/time/token/cost/reliability/intervention metrics and guidance-benefit assessments, task-family rubrics, clustered data splits, four baselines and provisional evidence thresholds before holdout exposure; map all decisions, unchanged draft requirements (including §22 items 1–12), review items R1–R8 and remaining gaps to explicit deferral or owning EC IDs whose text verifies them, amending that text through closeout; apply contract-level findings before IF-0-CONTRACT-1 freezes. Distinguish policy evaluation cases from the untouched release holdout and track exposure.

**Scope notes**

- Decompose into 3 lanes: BAML/contracts; vocabulary/toolchain; evaluation protocol. Contract lane owns shared manifests and schema generation. Evaluation establishes checks now, not at release time.
- Coverage: JD-001–JD-014, JD-037–JD-042, JD-047–JD-057, JD-064, JD-080–JD-082. Later phases implement their behavior.
- CONTRACT coverage work must resolve [manual review R1–R8](../research/roadmap-review/manual-claude/review.md) and sweep the original draft. Amend target ECs through CONTRACT closeout before planning affected later phases; record justified deferrals explicitly. These are pending obligations, not completed evidence.
- The [manual panel ruling](../research/roadmap-review/manual-rerun/round1/president-review.md) adds required CONTRACT plan inputs C2–C7 and coverage items P1–P7; record their owners and affected phases during CONTRACT. Use the [finding definitions and draft-sweep examples](../research/roadmap-review/manual-rerun/round1/opus-review.md), with the ruling controlling disagreements. Apply these alongside R1–R8. Review line numbers refer to the [reviewed snapshot](../research/roadmap-review/manual-rerun/round1/reviewed-roadmap.md).

**Non-goals**

- Production routing or claiming the proof's permissive models satisfy boundary rules.

**Key files**

- `baml.toml`, `baml_src/`, `schemas/`, `src/jevdrill/contracts.py`, `pyproject.toml`
- `docs/vocabulary.yaml`, `scripts/render_vocabulary.py`, `tests/contracts/`, `tests/evaluation/`

**Depends on**

- (none)

**Produces**

- IF-0-CONTRACT-1

**Spec closeout policy**

- schema: `spec_delta_closeout.v1`; decision: `roadmap_amendment`
- target surfaces: `specs/jevdrill-implementation-proposal.md`, this roadmap, `docs/vocabulary.yaml`
- evidence paths: `evidence/CONTRACT/spec-delta.json`, `evidence/CONTRACT/coverage.json`
- redaction_posture: `metadata_only`; missing/malformed evidence: `blocker_class=contract_bug`, non-human repair.

### Phase 2 — Durable routing core (ROUTE)

**Objective**

Implement progressive guidance discovery and task configuration selection through the CLI against strict contracts.

**Exit criteria**

- [ ] EC-ROUTE-1 — SQLite migrations, immutable identities, atomic durable decisions, duplicate/conflicting keys and reordered/corrected reports pass crash/retry/contention, locking and path tests on Linux/macOS/Windows; no unrecorded ready response escapes.
- [ ] EC-ROUTE-2 — Catalog import preserves provenance, reuse rights, source versions, benchmark comparability and admission; unchanged scans are idempotent. Guidance uses exact admitted or explicitly enabled revisions, no-skill candidates and at most two optional resources; conflicts/duplicates are rejected and required guidance fits context without truncation. Inventory freshness and native effort are verified. Setup proposals never install silently and readiness is rechecked afterward; access routes share a common interface.
- [ ] EC-ROUTE-3 — Deterministic selection enforces quality, time, hard constraints, raw/optional adjusted costs, unknown costs, stable ties and exact cache conditions. Recorded judgments replay decisions. JEV failure/invalid output/deadline exhaustion yields verified fallback or routing_failed. Privacy/provider restrictions bypass cloud JEV; actual token limits and oversize recovery are verified. Authorized attachment references preserve modality limits. Failed-acceptance rerouting links prior decisions/runs, distinguishes infrastructure from quality failure, bounds attempts/spend/time and addresses the failure. Structured explanations retain alternatives, exclusions, close calls and uncertainty.
- [ ] EC-ROUTE-4 — Context exclusions, project/workspace isolation, deletion tombstones and archive/key-failure primitives protect stored/queued data. Retention opt-out, separate raw-task/output controls and explicit deletion work from ROUTE; secrets and hidden reasoning are excluded. Settings precedence records the winning source without expanding authority. Linux/macOS/Windows paths preserve scope. CLI stdout is versioned JSON; startup, validation and persistence count toward the five-second deadline.
- [ ] EC-ROUTE-5 — BAML-authored discovery inputs, navigation state, typed questions/choices and results have strict shared fixtures and CONTRACT parity checks. State records offered choices, evidence/revision identities, unresolved paths, budget use and termination reasons. YAML declares canonical vocabulary before new public identifiers are implemented. Exact trace replay reconstructs questions, transitions and results without JEV calls; changed context, taxonomy, resources, inventory, policy or authorization invalidates reuse.
- [ ] EC-ROUTE-6 — The application itself advances domain → specialty → task → candidate descriptions → selected instructions. Fixtures prove multiple rounds, exact-match shortcuts, ambiguous and cross-domain paths, no suitable guidance, and useful candidates beyond the initial branch. Keep the full catalog outside JEV state; retrieve selected admitted instructions and enforce their context limits. Bound rounds, branch width, candidates, tokens, elapsed time and cost within the existing request deadline. Reject unoffered choices and prevent loops; exhausted budgets return supported uncertainty or explicit failure without relaxing constraints.
- [ ] EC-ROUTE-7 — Discovery results feed the existing configuration selector through public interfaces. Compare feasible combinations of model, native effort, guidance and execution route, retaining required guidance and the no-optional-guidance alternative. Fixtures show a selected skill yielding tasks with different eligible configurations, objective-dependent choices and rejection of known unsuitable options. Host-supplied candidate lists or accept-everything judgments cannot substitute for discovery acceptance.

**Scope notes**

- Decompose into 3 lanes: storage/lifecycle; catalog/inventory/context; costing/routing/JEV/guidance. Application integration and CLI have one named owner after lane interfaces agree.
- Replan lane interfaces around discovery contracts/state, catalog navigation, and selector integration; retain existing storage work. Freeze question schemas, transition/stop rules, packing, budget accounting and cache identity before implementation. Add shared contract fixtures; do not assume the existing per-candidate suitability question implements navigation.
- Token-bound clarification: discovery enforces input packing, finite calls and the shared deadline. An output planning reservation is not an enforceable provider output ceiling. Requested hard output or spending ceilings require demonstrated enforcement or rejection; no such guarantee follows from Boolean typing. This does not relax caller-requested constraints.
- Coverage: JD-015–JD-027, JD-036, JD-043–JD-044, JD-067–JD-073, JD-077–JD-078. Storage lifecycle primitives precede retained production traffic; scheduled automation follows in LEARN.

**Non-goals**

- Host execution, automatic policy learning or experiments.

**Key files**

- `src/jevdrill/{storage,settings,catalog,inventory,context,costing,routing,guidance,telemetry,application,cli}.py`
- `src/jevdrill/integrations/jev.py`, `tests/routing/`, `tests/storage/`, `tests/privacy/`

**Depends on**

- CONTRACT

**Produces**

- IF-0-ROUTE-1

**Spec closeout policy**

- schema: `spec_delta_closeout.v1`; decision: `canonical_spec_update`
- Explicit discovery amendment: add discovery contracts, a linked route-v2 wrapper and discovery lifecycle scope while preserving route-v1 validation. This authorizes the additive interface documentation, not governed-pipeline adoption.
- target surfaces: `docs/contracts.md`, `docs/route-interfaces.md`, `docs/vocabulary.yaml`, `docs/vocabulary.md`; evidence paths: `evidence/ROUTE/spec-delta.json`
- redaction_posture: `metadata_only`; missing/malformed evidence: `blocker_class=contract_bug`, non-human repair. Discovered contract changes require explicit amendment.

### Phase 3 — Harness integration and routing acceptance (HOST)

**Objective**

Deliver routing through the first host without bypassing its launch or permission rules.

**Exit criteria**

- [ ] EC-HOST-1 — Main and delegated/lane execution apply validated plans, report substitutions/observations, preserve permission restrictions and prevent recursive routing. Acceptance failures supply bounded rerouting context; guidance is not reinjected on retries and deactivates at task end, reporting host limitations. Dry runs never become execution-success evidence.
- [ ] EC-HOST-2 — Hooks and explicit reporting use one durable bounded queue redacted before persistence, idempotent acknowledgments and recovery; disconnects/capability mismatches include supported resolution advice. Host choices stay separate from check results; unknown telemetry is not fabricated. Hosts display pending local notices on their next connection.
- [ ] EC-HOST-3 — Linux/macOS/Windows contract suites and independent implementation/review/documentation evaluations pass predefined correctness and privacy gates using development/validation splits; reserve untouched holdout evaluation for PREPARE after thresholds freeze. Report uncertainty and routing overhead against all applicable baselines; insufficient evidence blocks performance claims.
- [ ] EC-HOST-4 — An installed CLI/companion flow takes an objective through discovery, returns selected guidance, lets the harness decompose it and routes at least two resulting tasks independently. Preserve objective/skill/task/decision links, guidance lifetime and substitutions. The harness may retain its current model or decline a recommendation. Tests must traverse production discovery and handoff paths rather than inject preselected guidance; no recursive routing or forced single model per skill.

**Scope notes**

- Decompose into 2 lanes: agent-harness adapter/queue; JEV Drill conformance/evaluation. Treat sibling-repository changes as separately owned work, with a shared fixture contract and explicit dependency handoff.
- ROUTE recovery steering: plan HOST against the new BAML-authored `RouteInputs`, inventory/catalog/settings/judgment records and strict management scopes in `docs/route-interfaces.md`. Supply verified model/access-route identities and pricing inputs; capability names never establish model availability. Pass `--remaining-budget-ms` after accounting for host spawn time and recheck readiness before launch. JD-083 permits estimated-cost routing without a requested ceiling. Spending, retry-spend or token ceilings require verified whole-run `execution_token_limits` and final host enforcement; context capacity and output estimates do not suffice. Deletion authority spans route/report producers within a project/workspace. Regenerate any HOST plan predating this amendment; it is not execution authority.
- Coverage: JD-003, JD-007, JD-013–JD-014, JD-036–JD-037, JD-046–JD-051, JD-065, JD-071, JD-073, JD-077–JD-078.
- JD-084 platform amendment: ordinary macOS routing/non-leased execution remains local. Leased macOS launch must reject before executor startup and recommend an explicitly configured Linux worker. Native macOS tests prove this rejection; Linux tests prove leased cleanup. No silent cross-machine forwarding or substitution of Linux evidence for native macOS proof.

**Non-goals**

- Additional host/provider implementations or immediate bakeoff execution.

**Key files**

- `src/jevdrill/integrations/`, `tests/conformance/`, `tests/evaluation/`
- Agent-harness: `phase-loop-runtime/src/phase_loop_runtime/{runner,launcher,observability}.py` and adapter tests

**Depends on**

- ROUTE

**Produces**

- IF-0-HOST-1

**Spec closeout policy**

- schema: `spec_delta_closeout.v1`; decision: `roadmap_amendment` (JD-083 and JD-084)
- target surfaces: shared event/adapter contracts and platform execution boundaries; evidence paths: `evidence/HOST/spec-delta.json`, `evidence/HOST/verification.json`
- redaction_posture: `metadata_only`; missing/malformed evidence: `blocker_class=contract_bug`, non-human repair.

### Phase 4 — Local learning and maintenance (LEARN)

HOST implementation handoff: replan this phase against metadata-only objective/discovery/task/decision/run bindings and durable objective tombstones. Distinguish selected versus applied plans, independent task deletion, unknown usage and host retain/decline preferences. Native synthetic HOST receipts establish software conformance only and cannot supply empirical quality floors, guidance effectiveness or promotion evidence.

**Objective**

Turn accumulated observed execution into scoped evidence with reliable retention and maintenance.

**Exit criteria**

- [ ] EC-LEARN-1 — Versioned comparable groups, minimum batches and periodic triggers update evidence under existing policy; reassessment supports multiple objectives without inventing counterfactual results. Missing/failed/canceled observations remain explicit.
- [ ] EC-LEARN-2 — Scheduled maintenance prevents overlap, resumes safely and yields to interactive work, with scheduler/pause/cancel evidence on Linux/macOS/Windows. Deterministic analysis is default; model-assisted analysis requires enabled capability and budgets.
- [ ] EC-LEARN-3 — Clock/key-failure fixtures on Linux/macOS/Windows verify 30-day active retention, seven-day archive grace, encrypted archival, one-year expiry notices, restoration and deletion propagation. Missing credentials, including headless Linux, retain pending content and issue inbox notices; never archive unencrypted. Inspectable export/import/backup verify integrity and portable recovery keys; apply deletion records before restored/imported analysis. Redacted measurements persist until deletion; policy validation becomes stale without automatic rollback.
- [ ] EC-LEARN-4 — Persistent local notices and opt-out/exclusion controls work; sharing is project-scoped by default, with explicit opt-in redacted user-wide learning. Benchmark assessments retain source metrics and objective history.
- [ ] EC-LEARN-5 — Observations link discovery choices and resulting task configurations to actual outcomes. Comparable evidence can inform later discovery and task selection; missing data, host preference, substitutions and measured failures stay distinct. Reclassification preserves raw measurements and prior objective versions. Tests prevent task evidence from becoming unsupported whole-skill or cross-domain claims. Policy writes remain limited to authorized candidate ordering; this criterion does not authorize learned navigation-policy changes.

**Scope notes**

- Decompose into 2 lanes: evaluation/analysis; maintenance/retention/notifications. Storage migrations have one owner. Coverage: JD-028–JD-031, JD-038–JD-045, JD-066–JD-072, JD-074–JD-076.

**Non-goals**

- Deliberate exploration, experiment execution or policy promotion.

**Key files**

- `src/jevdrill/{analysis,evaluation,storage,application,cli}.py`
- `tests/analysis/`, `tests/retention/`, `tests/maintenance/`

**Depends on**

- HOST

**Produces**

- IF-0-LEARN-1

**Spec closeout policy**

- schema: `spec_delta_closeout.v1`; decision: `no_spec_delta`
- target surfaces: learning/retention contracts; evidence paths: `evidence/LEARN/spec-delta.json`
- redaction_posture: `metadata_only`; missing/malformed evidence: `blocker_class=contract_bug`, non-human repair.

### Phase 5 — Comparisons and governed policy updates (EXPERIMENT)

**Objective**

Execute authorized comparisons and promote policies only with objective-specific evidence.

**Exit criteria**

- [ ] EC-EXPERIMENT-1 — Deduplicated proposals prioritize recurring uncertainty and expected benefit. Only after explicit experiment enablement and applicable standing authorization, default limits allow one background experiment/two candidates, with explicit compute/time and external per-experiment/daily caps. Default counts do not enable experiments; missing limits block execution.
- [ ] EC-EXPERIMENT-2 — Immediate host-accepted and deferred/internal paths respect deadlines, isolation and contention. Internal code runs require restricted containers; absent runtimes disable code experiments. Observed work retains host isolation. Linux/macOS/Windows pause/cancel/unavailability tests preserve honest partial and missing-context evidence; shadow runs never duplicate external side effects.
- [ ] EC-EXPERIMENT-3 — Host preference remains separate from checks; measurements support reclassification. Policy changes require separate authority, blinded evaluation on policy-held-out/regression cases, recorded exposure, predefined quality floors/tolerances and bounded rollout; the release holdout remains untouched. Revalidate policies made stale by deletion. Regression rolls back affected scopes and suspends the version, with verified fallback.
- [ ] EC-EXPERIMENT-4 — A preregistered development evaluation tests discovery and routing decisions against applicable CONTRACT baselines. Include ambiguous/cross-domain discovery, no useful optional guidance, objective changes and a skill with differing task needs. Predeclare acceptable choices and independent outcome checks; known unsuitable controls must expose always-admit/all-default behavior. Report selection errors, downstream outcomes, total routing overhead and objective-specific cost/time/quality with uncertainty. Executor bug-fixing scores alone cannot close this criterion; null results cannot justify benefit or promotion claims.

**Scope notes**

- Decompose into 2 lanes: scheduling/execution adapters; policy evaluation/promotion. Freeze experiment transitions from CONTRACT before either lane runs candidates. Coverage: JD-028, JD-032–JD-042, JD-065, JD-072, JD-074–JD-075, JD-079–JD-080.
- Owner-approved JD-078 exception: implement a BAML direct-provider adapter for the development calibration pilot. Reserve verified upper raw costs before calls, with no retries or fallback. Preserve the $1 per-experiment and $5 whole-pilot caps, two candidates, one experiment at a time, 120 seconds, 2 CPUs and 2 GiB. Generated code requires restricted containers; policy promotion remains disabled.

**Non-goals**

- Automatic objective recommendation or unbounded provider spending.

**Key files**

- `src/jevdrill/{experiments,analysis,evaluation,application}.py`, `src/jevdrill/integrations/`
- `tests/experiments/`, `tests/promotion/`, agent-harness comparison adapter/tests

**Depends on**

- LEARN

**Produces**

- IF-0-EXPERIMENT-1

**Spec closeout policy**

- schema: `spec_delta_closeout.v1`; decision: `no_spec_delta`
- target surfaces: experiment/promotion contracts; evidence paths: `evidence/EXPERIMENT/spec-delta.json`
- redaction_posture: `metadata_only`; missing/malformed evidence: `blocker_class=contract_bug`, non-human repair.

### Phase 6 — Release preparation and governance readiness (PREPARE)

**Objective**

Prepare a verifiable release candidate and canonicalization handoff.

**Exit criteria**

- [ ] EC-PREPARE-1 — Package installation/upgrade, migrations/recovery and full acceptance suites pass on supported platforms; version, changelog, docs and release inputs agree. Thresholds are frozen before holdout testing; unmet quality floors or insufficient evidence prevent promotion claims.
- [ ] EC-PREPARE-2 — Every accepted decision and unchanged draft requirement maps to implemented evidence or explicit deferred scope. Brownfield dry-run artifacts preserve source roles and YAML/BAML authority; HTML-to-harness representation checks preserve aliases, EC IDs, gates and dependencies. Adoption remains a separate action.
- [ ] EC-PREPARE-3 — Operational evidence, recovery instructions and a release-dispatch input manifest are reviewable; no publishing occurs. Ratification is reported only with required cross-vendor ablation evidence for Sol-authored plans.
- [ ] EC-PREPARE-4 — Supported-platform installed acceptance covers objective → discovery → harness decomposition → per-task configuration → observations → analysis with linked evidence. Verify every added drill-down criterion against the amended roadmap and current source. Missing progressive discovery blocks full release acceptance; the internal V0 checkpoint and standalone model benchmarks do not waive it. Preserve holdout isolation and separate publication authority.

**Scope notes**

- Decompose into 2 lanes: packaging/platform readiness; documentation/governance evidence. Release metadata has one owner. Coverage: JD-007, JD-046–JD-063, JD-080 and the complete decision coverage map.

**Non-goals**

- Release dispatch, canonical cutover, or fabricated review approval.

**Key files**

- `pyproject.toml`, release configuration, `docs/`, `specs/`, `tests/release/`
- `evidence/PREPARE/`, `evidence/decision-coverage.json`

**Depends on**

- EXPERIMENT

**Produces**

- IF-0-PREPARE-1

**Spec closeout policy**

- schema: `spec_delta_closeout.v1`; decision: `governed_pipeline_refresh` (metadata-only deferral)
- target surfaces: future canonical source registry and managed mirrors; evidence paths: `evidence/PREPARE/spec-delta.json`, `evidence/PREPARE/adoption-dry-run.json`
- redaction_posture: `metadata_only`; missing/malformed evidence: `blocker_class=contract_bug`, non-human repair. No `.pipeline/` writes authorized by this policy.

## Phase Dependency DAG

```text
CONTRACT → ROUTE → HOST → LEARN → EXPERIMENT → PREPARE
```

## Execution Notes

Each edge freezes a consumed contract: public schemas, durable decisions/events, real host outcomes, comparable evidence/lifecycle, then experiment/promotion behavior. Detailed lane plans can prepare fixtures for later phases early, but cannot claim dependent gates before evidence exists. Parallel execution is within each phase's disjoint lanes; no independent sibling phases are asserted.

CONTRACT owns shared manifests, vocabulary definitions and contract generators initially; later owners amend through its compatibility rules. Each phase assigns one writer to application wiring and migrations. Repository provenance is resolved. Use the applicable host worktree convention once a committed baseline permits worktree creation.

Operational platform/evaluation evidence goes to `evidence/<ALIAS>/verification.json` with runner identity, command, platform, versions and result. Substitute/proxy evidence requires a runner-stamped roadmap amendment before a gate verdict. Flag proof-cost limits when single-node evaluation exceeds roughly five minutes or cannot report multiple failures. Roadmap lint is not ratified review.

## Verification

Run now only: `phase-loop validate-roadmap specs/phase-plans-v1.md`.

Downstream plans must concretize these proposed commands and their tooling in CONTRACT; commands referencing new files are implementation deliverables, not currently runnable checks:

```sh
python3 scripts/render_vocabulary.py --check
python3 -m unittest discover -s tests -p 'test_catalog_*.py'
uv run pytest tests/contracts tests/routing tests/storage tests/privacy tests/conformance tests/evaluation tests/analysis tests/retention tests/maintenance tests/experiments tests/promotion tests/release
uv run ruff check src tests
uv run mypy src/jevdrill
uv run python scripts/check_generated_contracts.py
uv run python scripts/lint_vocabulary.py
uv run python scripts/check_import_boundaries.py
uv build
```

The phase-specific `automation.suite_command` must also validate its spec closeout evidence, operational evidence where required, and every referenced EC. Live benchmarks require declared budgets and retained metadata; the earlier single live JEV call is not a release-quality benchmark.
