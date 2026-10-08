## File: plans/phase-plan-v1-ROUTE.md

---
phase_loop_plan_version: 1
phase: ROUTE
roadmap: specs/phase-plans-v1.md
roadmap_sha256: 4ecbf27188b634d6ea5346cd67d61ab36d50d3ad0416a9a6d0d2602bb2698ab8
---

# ROUTE: Durable routing core

> Review status: revised after three substantive panel rounds. Final contract
> repairs are not yet independently cleared. Opus's reviewer stalled in all
> three rounds; the final president response failed format validation.
> Do not treat this plan as panel-approved. See phase-plan-v1-ROUTE_reviews.md.

## Context

Replan against the drill-down correction in `docs/drill-roadmap-map.md`.
The application, strict BAML contracts, catalog admission/retrieval, configuration
construction, deterministic ranking, storage and replay already exist. Preserve
them. Missing: application-owned successive questions, changing navigation state
and a discovery result consumed by later task routing.

Earlier ROUTE evidence covers the old scope only. EC-ROUTE-1–4 remain regression
obligations; EC-ROUTE-5–7 require new implementation and construction-path tests.
The prior plan's historical recovery allegations are not current findings.

Execute lanes serially. No sibling-repository edits, paid calls, private corpora,
holdout exposure, deployment or policy promotion. HOST owns real decomposition
and companion integration; ROUTE proves its public discovery/task boundary with
a synthetic caller. LEARN owns later analysis. No panel verdict establishes
software completion.

Length exception: slightly over 3,000 words preserves all seven criteria and the
interface/termination/accounting details requested by the panel; these details
are necessary to avoid another implementation that passes narrower checks.

## External Inputs

- Use the repository's locked BAML compiler/bridge and pinned TypeSafe client
  patch. Inspect current toolchain files before generation; do not replace the
  patch or silently change versions. Preserve usage attribution/parity tests.
- Existing native verification uses Linux plus macmini and native Windows via
  win-wsl transport. Probe read-only availability before declaring a platform
  unavailable; transfer only explicit public sources and synthetic fixtures.
- CONTRACT interfaces and metadata under `evidence/CONTRACT/` are read-only
  inputs. Repeat shared compatibility checks for added contracts.
- Existing five-second request deadline remains binding. No live latency claim
  is made; expensive discovery may return bounded uncertainty or failure.

## Interface Freeze Gates

- [ ] IF-0-ROUTE-1 — `Application.discover`, linked task routing through
  `Application.route`, durable discovery replay/deletion, and all seven ROUTE
  criteria pass current native evidence reduction.
- [ ] IF-0-VC-2 — `scripts/verify_route_phase.py` requires all seven criteria,
  path-entered negative controls and current source/fixture/command bindings;
  an old four-criterion report cannot pass.

SL-0 freezes the following design in BAML and `docs/route-interfaces.md`.
These names are planned interfaces, not claims that the types already exist.

### Public boundary and identities

Add `discover` to the CLI, accepting `DiscoveryInputs`: a new `DiscoveryEnvelope`
with operation "discover", work_objective_id/text, authorized context/attachments, binding
constraints, required guidance, catalog snapshot, versioned description records,
settings layers, discovery judgment policy and explicit discovery limits. No execution
model is selected at this stage; absence of executor inventory alone cannot
block objective guidance. Record taxonomy/catalog/content revisions.
Use `work_objective_id` for the work lifecycle; it is distinct from the existing
`OptimizationObjective.objective_id` metric identity. Add `DiscoveryScope`,
`DiscoveryInspectRequest` and `DiscoveryDeleteRequest` with operation "discover";
retain existing RequestEnvelope/CommandScope literals and v1 semantic validation.

`DiscoveryDescription` references an exact resource/revision/hash and provides
a human-authored short description. Validate it against the catalog and retain
its own digest. Existing catalogs remain valid for route v1; absent descriptions
are explicit unknowns in discovery, not inferred claims from resource names.
Derive taxonomy paths from validated domain/specialty/task-family metadata.
Freeze max_description_utf8_bytes at 2,048 by default; settings may only reduce
it. Oversized descriptions are unavailable, never silently truncated. This is
a packing limit, not proof that short text is safe: sanitize and treat it as data.

`DiscoveryResult` is a strict union: selected guidance, no optional guidance,
needs context, constraint conflict, or discovery failed. Include discovery ID,
work_objective_id, exact guidance references, bounded assembled instructions where
permitted, alternatives/uncertainty, termination reason and trace digest.
Distinguish complete rejection from unexamined candidates. An incomplete search
cannot assert that no useful guidance exists. Required guidance is never dropped.

Freeze precedence: missing authorized inputs give `needs_context`; infeasible
required guidance gives `constraint_conflict`; otherwise a supported feasible
optional resource gives `selected_guidance` (uncertain if incomplete). A complete
search with no feasible optional resource gives `no_optional_guidance`, recording
negative judgments versus incompatibility/context exclusions separately. An
incomplete search with no feasible supported resource gives `discovery_failed`.
The empty alternative is never positive discovery evidence. Complete means every
reachable optional leaf has a recorded judgment or deterministic infeasibility
reason; unknown leaves prevent it. An empty catalog can complete without calls,
but missing required guidance still conflicts.

Keep existing `RouteInputs` v1 fixtures unchanged. Add `DiscoveryRouteInputs`
with schema_version "2", nested v1 route inputs and a `DiscoveryRef` containing
discovery ID, work_objective_id and trace digest. The `route` boundary discriminates
versions before delegation to one internal selection path. Load references from
the same authorized project/workspace, verify scope and revisions, reject deleted
or stale discoveries, and include linkage in decision/cache/idempotency digests.
Do not trust caller-supplied selected instructions or treat the reference as
permission to execute. Fresh task constraints and inventory still control.
Only selected_guidance and no_optional_guidance may feed route-v2. Reject every
other variant before _prepare, cache/retry return and route commit. Propagate
termination/uncertainty into the linked decision. Test all variants with an
otherwise feasible quality-sufficient candidate, including uncertain selection
and successful empty optional guidance controls; never infer fallback authority.
Keep v1 digest construction unchanged. For v2, bind discovery identity/digest and
loaded revisions into request and cache digests. Intersect selected optional
resource/revision/hash triples with each fresh candidate's guidance_options;
undiscovered options cannot enter. Rebuild matched GuidanceRevision rows with
the concrete task_id, retaining authorized role/admission/authority and recounting
retrieved instructions. Preserve all feasible zero/one/two-resource combinations,
not just empty versus full pair. Rebind mandatory objective guidance for the task
and combine it with active_guidance without duplicate injection or lost authority;
identical required references coalesce, conflicts fail. A missing required
resource fails; missing optional capability excludes that option. Verify inherited
mandatory constraints before accepting additional task constraints.
Route-v2 rejects non-null nested catalog_query and skips narrow, using the full
validated catalog only after substituting candidate guidance_options. Required
references coalesce only on equal resource/revision/hash/role/authority/admission;
differences fail. Task constraints must be equal or stricter; weakening fails.
Freeze the field-wise order against discovery's inherited HardConstraints:
total_deadline_ms/context_token_limit/max_attempts may only decrease; local_only
may only change false→true; governing_instruction_refs may only grow. A restricted
allowed_providers set may only shrink to a nonempty subset (empty means unrestricted
in v1); an unrestricted parent permits either. A null spending ceiling may gain a
cap; existing caps may only decrease in the same currency. Execution token limits
may be added to null or decreased component-wise, never removed. Excluded-path
settings are unioned and acceptance requirements are retained unchanged by ID,
with additions allowed. Unknown or incomparable changes fail. These are per-task
limits, not an asserted aggregate work-objective spending budget.

### Navigation and judgment semantics

Pure transitions live in a small new `discovery.py` module; register its YAML
vocabulary and import permissions. Keep catalog identity/retrieval in
`catalog.py` and provider effects in `integrations/jev.py`.
`DiscoveryState` records current frontier, deferred paths, examined choice IDs,
supported leaf candidates, omitted/unavailable evidence and remaining budgets.

`next_question(state)` emits a versioned `DiscoveryQuestion` at domain,
specialty, task-family or resource level, with stable offered option IDs and a
digest over state plus options. `apply_answers(state, answers)` accepts only
answers bound to that question digest; duplicate, unknown or stale IDs fail.

Use BAML Boolean judgments per offered option through a distinct
`ObserveDiscoveryOption` function and the existing patched observation path.
Add DiscoveryJudgmentPolicy and DiscoveryJudgmentRecord with function_revision
"ObserveDiscoveryOption-v1"; preserve JudgeCandidate-v1-only contracts. Shared
fixtures reject route policies as discovery policies and vice versa.
Drill aggregates those bound answers into navigation choices; do not assume a
new multi-select provider feature. Missing/failed answers remain unknown.
Question templates ask whether a path merits examination or a described resource
suits the objective; a category answer is not resource suitability evidence.

Navigation never calls catalog.narrow; that helper stays unchanged for v1.
Maintain preferred and deferred FIFO queues, assigning monotonic enqueue sequence
numbers; insert same-batch siblings in stable ID order. Category true appends
unvisited children to preferred; false appends them to deferred behind already
queued alternate domains. Unknown records an unresolved subtree without repeating
its question. Alternate queues whenever both have work, starting with preferred;
otherwise serve the nonempty queue. Active width caps simultaneously materialized
options for the chosen frontier; keep remaining options as cursors, requeued at
the tail with new sequence numbers. Queue metadata is not active context. Never
re-sort by last-service age. This lets answers guide discovery while
reserving opportunities to recover from classification mistakes. If both queues
empty, unresolved subtrees remain uncertainty, not rejection. Use a visited set
and finite work allowance. Test that swapping category answers changes traversal
and a useful alternate branch remains reachable with sufficient budget.
Exact resource/revision or unique alias matches can skip
taxonomy levels but cannot skip admission or resource suitability checks;
ambiguous aliases preserve alternatives. Required resources bypass optional
ranking but must remain admitted, compatible and within context.

At resource leaves retain judged-suitable guidance, including the empty optional
set, for deterministic compatible selection of at most two optional resources.
Stable (resource_id, revision) ordering breaks supported-leaf ties; record other
leaves as alternatives. Category false does not permanently exclude descendants.
Retrieve full instructions only for shortlisted leaves, never for every branch
or into JEV navigation context. Discovery does not certify model/task quality.
Later task routing rechecks applicability, conflicts, required guidance and
downstream context before constructing model/effort/route combinations.

### Bounds, privacy and durable trace

Limits explicitly specify rounds, active branch width, examined candidates,
provider calls, input packing allowance, output planning reservation, optional
hard_output_token_limit and optional raw spending ceiling.
Intersect with judgment policy, settings and remaining request time; no implicit
undeclared scope or recursive budget reset. A round is one question and its
bounded option judgments. Reserve call/token/cost allowance before each attempt,
retain reservations when usage is missing, and count failed attempts.
Reject a configured ceiling if the adapter cannot enforce its upper bound.
The pinned client exposes no output-token enforcement. A non-null hard output
limit therefore rejects before dispatch; a planning reservation is not that limit.
With no hard output limit, finite calls/input/time still bound work. A requested
spending ceiling requires verified input pricing and a known zero output rate;
unknown or positive output pricing cannot establish that ceiling. Without a
spending ceiling, missing prices remain unknown. Test a positive generated-BAML
loopback call with no hard output limit and synthetic zero-output-rate pricing,
plus rejection of unsupported requested ceilings before any HTTP request. Do not
infer real provider pricing from fixtures or claim output-token enforcement.
Preserve the existing conservative packing method and label it as a bound,
not measured token use. Keep reserve time for durable commit; never extend the
five-second CLI deadline, with at least the existing 50 ms commit margin. This
ledger covers one discovery request, not separate later route invocations.
Deferred branches and omitted evidence stay visible.

Sanitize context, descriptions and metadata before provider submission or
persistence. Catalog instructions stay local except explicitly returned selected
guidance. Hard privacy/provider restrictions apply before every call. On
exhaustion, only already supported feasible guidance may be returned with
uncertainty; otherwise return an explicit non-success result.
Provider payload is an allowlist: authorized sanitized objective/context,
question level/digest, stable option IDs and descriptions or explicit unknowns.
Never send instruction bodies, rights/source records or arbitrary catalog fields.

Persist `DiscoveryTrace` with versioned compact transition records, offered
IDs, bound answers, evidence digests, budget deltas and final result before
success escapes. Raw task/description text follows existing retention settings;
do not persist hidden reasoning. Metadata-only replay reconstructs decisions
from validated transitions and recorded answers, without regenerating private
prompts or provider calls; erased payloads are unavailable, never fabricated.
Retain initial topology/option IDs, transition-policy version, feasibility flags,
admitted references and per-round deltas sufficient for replay without text.
Test raw-retention opt-out and changed live catalogs; replay uses recorded facts.
If privacy rules exclude even those facts, mark replay unavailable, not reconstructed.
Exact cache reuse additionally binds sanitized context, descriptions, taxonomy,
resources, policy/function/model versions, scope, authorization and relevant
freshness. Replay and cache reuse are distinct operations.

Extend operation-scoped idempotency and deletion to discovery. Namespace its
lifecycle by project/workspace/discover/work_objective_id, separately from task
tombstones; producer authorization still applies. Deleting it prevents
new linked routing or replay. Existing linked task records follow their own
deletion scopes; they cannot resurrect the discovery. Same-key conflict checks,
lost-response retries and atomic trace/result commit mirror current routing.
Mint discovery ID once in the durable reservation, keyed by envelope idempotency
key and scoped request digest. Same-key changed payload conflicts. Check linked
discovery admission/tombstone and route commit within one storage transaction;
an application-level check before the transaction is insufficient.
One unique discovery lifecycle row per project/workspace/work_objective_id owns
all immutable request attempts. Different idempotency keys may create distinct
attempts under that live parent; they never reset an earlier request's ledger.
Objective deletion tombstones the parent permanently and atomically
invalidates every linked discovery, retry, cache and metadata replay, across
producers within the authorized project/workspace. Recheck tombstones during
discovery commit and late-observation ingestion; test cache/retry after deletion.
Test two attempts under one parent: deletion prevents either returning cached
success and prevents a new key recreating the objective. Optional result refs
alone form the route-v2 allowlist; omitted alternatives are explanatory only.
New calls after an interrupted attempt must not forget reserved budget: persist
attempt reservations before dispatch and either resume from recorded observations
or return explicit interrupted failure without silently repeating the call.
Recovery of an existing nonterminal attempt dispatches no new provider work:
reduce durable observations to a supported partial result or interrupted failure.
Each invocation still has its own five-second response deadline, but cannot renew
that attempt's provider allowance. Returning a committed result is replay, subject
to current deletion/status checks. Test retry after the original invocation expires.

## Lane Index & Dependencies

- SL-0 — Contracts and vocabulary; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 — Pure navigation; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 — Bounded judgment and persistence; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 — Application and CLI; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 — Verification and handoff reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: (none); Parallel-safe: no

## Lanes

### SL-0 — Contracts and vocabulary

- **Scope**: Freeze additive discovery/link contracts, canonical names and strict validation.
- **Owned files**: `baml_src/**`, `src/baml_sdk/**`, `schemas/**`, `src/jevdrill/contracts.py`, `docs/vocabulary.yaml`, `docs/vocabulary.md`, `docs/contracts.md`, `docs/route-interfaces.md`, `tests/contracts/**`, `scripts/contract_consumer.mjs`
- **Interfaces provided**: `discovery_contracts`
- **Interfaces consumed**: existing strict parsing, canonical digests, generated schemas and usage contracts
- **Parallel-safe**: no
- **Tasks**:
  - test: Add shared positive/negative discovery and route-v2 fixtures; preserve v1 acceptance. Reject spoofed references, invalid unions, coerced scalars, malformed budgets and unsupported versions.
  - impl: Author interfaces above, operation/lifecycle additions and pure-module import permissions. Generate through existing tooling; do not edit generated fields manually. Add both real and loopback discovery functions using the existing patched client.
  - verify: `uv run pytest tests/contracts`; `node scripts/contract_consumer.mjs tests/contracts/fixtures`; `uv run python scripts/check_generated_contracts.py`; `uv run python scripts/render_vocabulary.py --check`; `uv run python scripts/lint_vocabulary.py`.

### SL-1 — Pure navigation

- **Scope**: Build bounded catalog traversal and deterministic transitions.
- **Owned files**: `src/jevdrill/discovery.py`, `src/jevdrill/catalog.py`, `tests/discovery/**`, `tests/catalog/**`
- **Interfaces provided**: `discovery_transitions`
- **Interfaces consumed**: `discovery_contracts`
- **Parallel-safe**: no
- **Tasks**:
  - test: Cover multi-round paths, exact shortcuts, alias ambiguity, cross-domain recovery, absent descriptions, all-rejected versus unexamined, cycles, stable permutations and all budget boundaries.
  - impl: Implement next_question/apply_answers, metadata projection, deferred traversal and leaf selection. Preserve catalog narrow/retrieve for legacy routing. No imports of application, storage or providers.
  - verify: `uv run pytest tests/discovery tests/catalog`; `uv run python scripts/check_import_boundaries.py`.

### SL-2 — Bounded judgment and persistence

- **Scope**: Bind real BAML navigation calls and recoverable storage to frozen transitions.
- **Owned files**: `src/jevdrill/integrations/jev.py`, `src/jevdrill/storage.py`, `tests/integrations/**`, `tests/storage/**`, `tests/privacy/test_discovery_privacy.py`
- **Interfaces provided**: `discovery_effects`
- **Interfaces consumed**: `discovery_contracts`, `discovery_transitions`
- **Parallel-safe**: no
- **Tasks**:
  - test: Loopback transport exercises generated ObserveDiscoveryOption and partial usage; inject invalid binding, timeout, missing usage, crash after reservation, duplicate/conflicting keys and deletion races.
  - impl: Add adapter methods consuming one shared deadline/budget ledger, preserving ObserveCandidate behavior. Add migrations, reservation/trace/result transactions, scoped lookup and deletion-safe replay. No provider call inside a database transaction.
  - verify: `uv run pytest tests/integrations tests/storage tests/privacy/test_discovery_privacy.py`.

### SL-3 — Application and CLI

- **Scope**: Connect discovery to public commands and existing task selection.
- **Owned files**: `src/jevdrill/application.py`, `src/jevdrill/cli.py`, `tests/application/**`, `tests/cli/**`, `tests/privacy/test_application_privacy.py`
- **Interfaces provided**: `discovery_application`
- **Interfaces consumed**: `discovery_contracts`, `discovery_transitions`, `discovery_effects`, existing inventory/context/settings/guidance/routing
- **Parallel-safe**: no
- **Tasks**:
  - test: Public discover→two linked route requests, production construction with synthetic inputs; one task can choose a different configuration. Also keep catalog fixed and change objectives to require different supported guidance. Cover every discovery status, every equal/stricter/relaxed constraint field and cached status rejection. Force branch mistakes, undiscovered inventory options, bad references, required-guidance conflicts, provider privacy rejection, deletion races and commit failure.
  - impl: Orchestrate state advancement; add discover, inspect-discovery (--discovery-id, --scope, --replay) and delete-discovery (--work-objective-id, --scope). Adapt route-v2 into the existing _prepare/select_plan path using the frozen conversion above; never manufacture inventory availability. Retain all old route outcomes and constraint handling.
  - impl: Return canonical JSON within startup-to-commit deadline; preserve existing output-size limits and reject oversize selected instructions without truncation. Revalidate discovery linkage before route commit, including concurrent deletion.
  - verify: `uv run pytest tests/application tests/cli tests/privacy/test_application_privacy.py`.

### SL-4 — Verification and handoff reducer

- **Scope**: Prove all ROUTE criteria and publish accurate readiness for HOST.
- **Owned files**: `scripts/verify_route_phase.py`, `tests/verification/test_route_phase.py`, `evidence/ROUTE/**`, `README.md`, `docs/route-readiness.md`, `docs/drill-roadmap-map.md`, `docs/roadmap-status.md`
- **Interfaces provided**: `route_acceptance`, IF-0-ROUTE-1, IF-0-VC-2
- **Interfaces consumed**: `discovery_contracts`, `discovery_transitions`, `discovery_effects`, `discovery_application`
- **Parallel-safe**: no
- **Tasks**:
  - test: Reject four-criterion manifests, skipped controls, missing discovery tests, stale input/command digests and missing native platforms. Keep existing verifier adversarial tests.
  - impl: Extend REQUIRED_TEST_PATHS, lint/type/fixture inputs and coverage requirements to seven ECs. Preserve all old checks. Collect native matrix with installed CLI, BAML loopback, crash/privacy and Python/Node parity. Bind coverage to real test outcomes, not just filenames.
  - impl: Archive earlier metadata before replacing current reports; write truthful spec-delta/coverage and HOST handoff documenting discovery/route-v2 boundaries. No empirical quality claims from scripted judgments. Do not mark downstream phases complete.
  - verify: `uv run pytest tests/verification/test_route_phase.py`; `uv run python scripts/verify_route_phase.py`.

## Execution Notes

Ownership sets are disjoint. Reopen the owning lane for interface repairs; no
lane writes another lane's files. No dependency or environment change is planned.
If one becomes necessary, amend SL-0 ownership for manifests/locks before edits.
Only the final reducer writes synthesized readiness and phase evidence.
Native-platform unavailability permits partial local evidence, not gate closure.
Broad existing dirty changes must be inventoried and preserved before execution.

## Verification

Effective `automation.suite_command`: `uv run python scripts/verify_route_phase.py`.

During implementation, run narrow lane commands first; the aggregate collector
retains its existing tests, generation, vocabulary/import checks, Ruff, mypy,
build, installed-package and cold-start checks. Add discovery to all scoped
inputs. Use --local-only for partial native collection and --reduce-only for
the final current-source matrix. Preserve the existing ten-minute collector
limit and flag runs exceeding the roadmap's five-minute proof-cost target.
Neither changes the five-second product deadline.

Planning performs no product tests/builds or model-quality experiment.
New command paths/tests above are implementation deliverables. Deterministic
false-answer controls and loopback BAML tests prove software behavior; independent
live quality evidence belongs to HOST/EXPERIMENT and later release acceptance.

## Acceptance Criteria

- [ ] EC-ROUTE-1 — proven by `uv run pytest tests/storage tests/application tests/cli` and aggregate matrix; falsified by commit failure returning success or deleted discovery being reused through the entered application path.
- [ ] EC-ROUTE-2 — proven by `uv run pytest tests/catalog tests/inventory tests/guidance tests/application`; falsified by a discovered unadmitted revision reaching selection.
- [ ] EC-ROUTE-3 — proven by `uv run pytest tests/routing tests/costing tests/integrations tests/application`; falsified by forbidden provider traffic, stale-authority reuse or unsupported cost-cap compliance.
- [ ] EC-ROUTE-4 — proven by `uv run pytest tests/privacy tests/context tests/settings tests/cli`; falsified by a retained/sent excluded sentinel or a success after the shared deadline.
- [ ] EC-ROUTE-5 — proven by `uv run pytest tests/contracts tests/discovery tests/storage` plus shared Node fixtures; falsified by accepting unoffered answers, cross-scope reuse or any provider call during trace replay.
- [ ] EC-ROUTE-6 — proven by `uv run pytest tests/discovery tests/application tests/integrations`; falsified by replacing production next_question with a one-pass filter, abandoning a recoverable alternate branch, or exceeding a reserved limit.
- [ ] EC-ROUTE-7 — proven by `uv run pytest tests/application tests/cli`; falsified by bypassing discover with preselected guidance, admitting a known-unsuitable control, or forcing identical task configurations despite differing constraints.
- [ ] IF-0-VC-2 — proven by `uv run pytest tests/verification/test_route_phase.py` and `uv run python scripts/verify_route_phase.py --reduce-only`; falsified by an old four-criterion or stale-platform report passing.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `canonical_spec_update`
- target surfaces: `docs/contracts.md`, `docs/route-interfaces.md`, `docs/vocabulary.yaml`, `docs/vocabulary.md`
- evidence paths: `evidence/ROUTE/spec-delta.json`, `evidence/ROUTE/verification.json`, `evidence/ROUTE/coverage.json`
- redaction posture: `metadata_only`
- downstream handling: replan HOST against discovery/route-v2; retain downstream stale-plan notices

This records additive interface documentation, not governed-pipeline adoption.
The roadmap permits explicit contract amendments; incompatibilities beyond these
additions require a new recorded amendment before implementation.


## File: baml_src/ns_typesafe_patch/client.baml

// Derived from BoundaryML/baml, baml-language-0.20.1 (Apache-2.0).
// Modified by JEV Drill: local namespace. See LICENSE and UPSTREAM.md.
/// TypeSafe's JEV classifier (POST {base_url}/systemone).
/// Bool and float outputs use Noul; enums and finite unions use Choice.
/// Classes are flattened into one question per leaf. Unsupported output
/// types, empty instructions, tools, and media are rejected before HTTP.
/// JEV does not stream. Use invoke or an ordinary LLM function call.
class Client {
    model: string,
    api_key: ai.Credential?,
    base_url: ai.Credential?,
    request_timeout_ms: int?,
    capture_wire: bool,

    /// Construction is pure. Credentials resolve when invoking, using
    /// TYPESAFE_API_KEY unless an explicit credential is provided.
    function new(
        model: string = "jev-latest",
        api_key: ai.Credential? = env.TYPESAFE_API_KEY,
        base_url: ai.Credential? = "https://api.typesafe.ai/v1",
        request_timeout_ms: int? = null,
        capture_wire: bool = true,
    ) -> Client {
        Client {
            model: model,
            api_key: api_key,
            base_url: base_url,
            request_timeout_ms: request_timeout_ms,
            capture_wire: capture_wire,
        }
    }

    implements ai.Client {
        function id(self) -> string {
            `typesafeai/${self.model}`
        }

        /// Preview the request without resolving credentials or performing IO.
        function render(self, input: ai.ModelTurnInput) -> baml.http.Request {
            root.typesafe_patch.internal.request(self, input, root.typesafe_patch.internal.plan(input), true) catch_all (e) {
                _ => throw ai.errors.normalize(e),
            }
        }

        function invoke(self, input: ai.ModelTurnInput) -> ai.ModelTurn {
            root.typesafe_patch.internal.invoke(self, input) catch_all (e) {
                _ => throw ai.errors.normalize_invoke(e),
            }
        }
    }
}


## Authoritative ROUTE roadmap section

 Durable routing core (ROUTE)

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



## Source excerpt: baml_src/contracts.baml:19

```
class GuidanceRevision {
    resource_id: string, revision: string, content_hash: string, role: string,
    admission: "policy_admitted" | "explicitly_enabled", authority: string,
    task_id: string, token_count: int?,
}
class ExecutionPlan {
    execution_plan_id: string, predecessor_plan_id: string?, model_id: string,
    resolved_model_revision: string?, provider: string, access_route: string,
    native_effort: NativeEffort, optional_guidance: GuidanceRevision[],
    required_guidance: GuidanceRevision[], guidance_action: "none" | "inject",
    required_capabilities: string[], harness_id: string, execution_target_id: string,
}
class RequestEnvelope {
    schema_version: "1", request_id: string, operation: "route" | "report",
    project_id: string, workspace_id: string, harness_id: string,
    execution_target_id: string, created_at: string, idempotency_key: string,
    extensions: baml.Map<string, string>,
}
class AcceptanceRequirement { requirement_id: string, description: string, source: "user" | "task_family" | "inferred", evaluator_ref: string }
class OptimizationObjective { objective_id: string, version: string, metric_id: string, direction: "minimize" | "maximize", routing_cost_basis: "raw" | "adjusted", acceptance_requirements: AcceptanceRequirement[] }
class AttachmentReference { reference: string, modality: "image" | "audio" | "video" | "document", authorized: bool, text_representation: string?, representation_source: string? }
class ExecutionTokenLimits { input_tokens: int, output_tokens: int }
class HardConstraints { local_only: bool, allowed_providers: string[], spending_ceiling: Money?, total_deadline_ms: int, context_token_limit: int, max_attempts: int, governing_instruction_refs: string[], execution_token_limits: ExecutionTokenLimits? }
class RetryContext { prior_routing_decision_id: string, prior_execution_run_id: string, failure_class: "infrastructure" | "quality", failure_summary: string, remaining_attempts: int, remaining_time_ms: int, remaining_spend: Money? }
class Capabilities { declared: string[], runtime: string[], inventory_revision: string, verified_at: string, expires_at: string }
class VersionReferences { settings_revision: string, context_revision: string, catalog_revision: string, policy_revision: string, evidence_revision: string }
class RouteRequest {
```

## Source excerpt: baml_src/contracts.baml:175

```
    candidate_id: string, model_id: string, resolved_model_revision: string,
    provider: string, access_route: string, local: bool, native_effort: NativeEffort,
    supported_efforts: string[], declared_capabilities: string[], runtime_capabilities: string[],
    required_capabilities: string[], verified_at: string, expires_at: string, source: string,
    context_token_limit: int, output_token_limit: int, token_counter_revision: string,
    quality_sufficient: bool?, satisfied_requirements: string[], completion_time_ms: int?,
    evidence_strength: "measured" | "judgment" | "unknown", evidence_refs: string[],
    rates: RateCard?, default: bool, guidance_options: GuidanceRevision[],
    addresses_failures: string[], execution_token_limits: ExecutionTokenLimits?,
}
class InventorySnapshot {
    schema_version: "1", revision: string, target: string, source_version: string,
    verified_at: string, expires_at: string, candidates: CandidateSnapshot[],
}
class CatalogResource {
    resource_id: string, revision: string, content_hash: string, rights: string,
    admission: "policy_admitted" | "explicitly_enabled" | "unadmitted",
    source_occurrences: string[], aliases: string[], domain: string, specialty: string,
    task_family: string, facets: string[], benchmark_protocol: string?, benchmark_split: string?,
    benchmark_effort: string?, instructions: string, conflicts: string[],
}
class CatalogSnapshot { schema_version: "1", revision: string, resources: CatalogResource[] }
class CatalogQuery { domain: string, specialty: string, task_family: string, facets: string[], max_branches: int }
class SettingsOverride {
    routing_cost_basis: ("raw" | "adjusted")?, retain_raw_tasks: bool?, retain_raw_outputs: bool?,
    local_analysis_enabled: bool?, experiment_enabled: bool?, model_analysis_enabled: bool?,
    default_plan_id: string?, routing_deadline_ms: int?, excluded_paths: string[]?,
}
class SettingsLayer {
    source: "product" | "user" | "project" | "directory" | "personal_project" | "request",
    values: SettingsOverride,
}
class JudgmentPolicy {
    enabled: bool, cloud_allowed: bool, max_calls: int, max_candidates: int,
    max_input_tokens: int, max_output_tokens: int, spending_ceiling: Money?,
    rates: RateCard?, model_revision: string, function_revision: "JudgeCandidate-v1",
    token_counter_revision: string,
}
class RouteInputs {
    schema_version: "1", request: RouteRequest, inventory: InventorySnapshot?,
    catalog: CatalogSnapshot?, settings_layers: SettingsLayer[], judgment_policy: JudgmentPolicy?,
    completion_time_limit_ms: int?,
    catalog_query: CatalogQuery?,
}
class JudgmentRecord {
    schema_version: "1", function_revision: "JudgeCandidate-v1", model_revision: string,
    candidate_digest: string, judgments: baml.Map<string, bool>, measurements: Measurement[],
}
class CommandScope {
    project_id: string, workspace_id: string, producer: string, operation: "route" | "report",
}
class NoticeRequest { schema_version: "1", scope: CommandScope }
class NoticeInbox { schema_version: "1", notices: LocalNotice[] }
class InspectRequest { schema_version: "1", scope: CommandScope, decision_id: string, replay: bool }
class DeleteRequest { schema_version: "1", scope: CommandScope, task_id: string }
class ReplayBundle {
    schema_version: "1", routing_decision_id: string, task_id: string, request_digest: string,
    cache_digest: string, decision: RoutingDecision, judgments: JudgmentRecord?,
}

class LearningContext {
    task_id: string, routing_decision_id: string, task_family: string,
    task_group: string, environment_revision: string, isolation_revision: string,
    evaluator_ref: string, rubric_revision: string, local_analysis_enabled: bool,
    share_user_wide: bool,
```

## Source excerpt: src/jevdrill/application.py:225

```
                if snapshot["revision"] != capability["inventory_revision"] or not fresh(
                    capability["verified_at"], capability["expires_at"]
                ):
                    raise ContractError("inventory revision or freshness mismatch")
                catalog = inputs["catalog"]
                resources = [] if catalog is None else catalog["resources"]
                if catalog is not None:
                    if _sanitize(catalog) != catalog:
                        raise ContractError("excluded catalog content")
                    catalog_digest(resources)
                    if catalog["revision"] != request["versions"]["catalog_revision"]:
                        raise ContractError("catalog revision mismatch")
                    query = inputs.get("catalog_query")
                    if query is not None:
                        resources = narrow(
                            resources,
                            query["domain"],
                            query["specialty"],
                            query["task_family"],
                            query["facets"],
                            query["max_branches"],
                        )
                prepared = self._prepare(request, snapshot, resources, settings, deadline)
                for row in prepared:
                    row["completion_time_limit_ms"] = inputs.get("completion_time_limit_ms")

                def observe(event: object) -> None:
                    measurements = jev_usage_measurements(event)
                    invocation_id = getattr(event, "invocation_id", None)
                    if measurements and isinstance(invocation_id, str):
                        recorded[invocation_id] = measurements

                policy = inputs["judgment_policy"]
                feasibility = select_plan(request, prepared)
                judgment_eligible = (
                    {
                        row["candidate_id"]
                        for row in feasibility["details"]["exclusions"]
                        if row["reasons"] == ["quality_unknown_or_insufficient"]
                    }
                    if feasibility["status"] != "constraint_conflict"
                    else set()
                )
                offered = [
                    row
                    for row in prepared
                    if row["candidate_id"] in judgment_eligible
                    and row["quality_sufficient"] is None
                ]
                can_judge = (
                    policy
                    and policy["enabled"]
                    and policy["cloud_allowed"]
                    and not request["hard_constraints"]["local_only"]
                    and not request["recursion_bypass"]
                )
                if can_judge and offered:
                    assert policy is not None
                    if policy["rates"] is not None and not fresh(
                        policy["rates"]["verified_at"], policy["rates"]["expires_at"]
                    ):
                        raise ContractError("stale judgment rates")
                    offered = offered[: min(policy["max_candidates"], policy["max_calls"])]
                    public: tuple[Mapping[str, Any], ...] = tuple(
                        {key: value for key, value in row.items() if key not in {"cost"}}
                        for row in offered
```

## Source excerpt: src/jevdrill/application.py:419

```
    def _prepare(
        self,
        request: Mapping[str, Any],
        snapshot: Mapping[str, Any],
        resources: list[dict[str, Any]],
        settings: Mapping[str, Any],
        deadline: float,
    ) -> list[dict[str, Any]]:
        prepared = []
        host_permissions = set(request["capabilities"]["declared"]) & set(
            request["capabilities"]["runtime"]
        )
        for candidate in sorted(snapshot["candidates"], key=lambda row: row["candidate_id"]):
            counter = ConservativeTokenCounter(
                {candidate["resolved_model_revision"]: candidate["token_counter_revision"]}
            )
            options = candidate["guidance_options"]
            combinations = [()] + [
                combo for count in (1, 2) for combo in itertools.combinations(options, count)
            ]
            for optional in combinations:
                if monotonic() >= deadline - 0.05:
                    raise ContractError("candidate preparation deadline expired")
                row = dict(candidate)
                row["candidate_id"] += ":" + canonical_digest(list(optional))[:12]
                row["default"] = (
                    row["default"] or settings["default_plan_id"] == candidate["candidate_id"]
                )
                row["exclusion_reasons"] = []
                row["available"] &= set(row["required_capabilities"]) <= host_permissions
                row["verified_at"] = max(
                    row["verified_at"],
                    snapshot["verified_at"],
                    request["capabilities"]["verified_at"],
                )
                row["expires_at"] = min(
                    row["expires_at"], snapshot["expires_at"], request["capabilities"]["expires_at"]
                )
                required = copy.deepcopy(request["active_guidance"])
                optional_rows = copy.deepcopy(list(optional))
                try:
                    contents = []
                    for guidance in required + optional_rows:
                        if guidance["task_id"] != request["task_id"]:
                            raise ContractError("guidance task scope mismatch")
                        text = retrieve(resources, guidance)
                        guidance["token_count"] = counter.count(
                            text, candidate["resolved_model_revision"]
                        )
                        contents.append(text)
                    identities = {item["resource_id"] for item in required + optional_rows}
                    if any(
                        set(resource["conflicts"]) & identities
                        for resource in resources
                        if resource["resource_id"] in identities
                    ):
                        raise ContractError("guidance conflict")
                    text = json.dumps(
                        {
                            "task": request["task_representation"],
                            "acceptance": request["optimization_objective"][
                                "acceptance_requirements"
                            ],
                            "attachments": request["attachment_refs"],
                            "governing": request["hard_constraints"]["governing_instruction_refs"],
                            "guidance": contents,
                        },
                        sort_keys=True,
                    )
                    tokens = counter.count(text, candidate["resolved_model_revision"])
                    limit = min(
                        candidate["context_token_limit"],
                        request["hard_constraints"]["context_token_limit"],
                    )
                    select_guidance(required, optional_rows, limit)
                    if tokens + candidate["output_token_limit"] > limit:
                        raise ContractError("complete context exceeds limit")
                    execution_limits = candidate.get("execution_token_limits")
                    if execution_limits is not None and tokens > execution_limits["input_tokens"]:
                        raise ContractError("initial input exceeds execution token limit")
```

## Source excerpt: src/jevdrill/integrations/jev.py:15

```
from ..contracts import ContractError, canonical_digest, jev_usage_measurements, parse_contract


class JevAdapter:
    def __init__(
        self,
        policy: Mapping[str, Any] | None = None,
        on_event: Callable[[object], None] | None = None,
    ) -> None:
        self.policy = None if policy is None else parse_contract("JudgmentPolicy", policy).payload()
        self.on_event = on_event

    def bounded_candidates(
        self, task: str, candidates: tuple[Mapping[str, Any], ...]
    ) -> tuple[Mapping[str, Any], ...]:
        if self.policy is None:
            return ()
        remaining = self.policy["max_input_tokens"]
        selected = []
        for row in candidates[: min(self.policy["max_calls"], self.policy["max_candidates"])]:
            wire = candidate_request_shape(task, json.dumps(dict(row), sort_keys=True))
            tokens = len(wire.encode())
            if tokens <= remaining:
                selected.append(row)
                remaining -= tokens
        return tuple(selected)

    def judge(
        self, task: str, candidates: tuple[Mapping[str, Any], ...], deadline: float
    ) -> Mapping[str, Any]:
        if deadline <= monotonic():
            raise ContractError("judgment deadline expired")
        policy = self.policy
        if policy is None or not policy["enabled"] or not policy["cloud_allowed"]:
            raise ContractError("judgment not authorized")
        if (
            policy["model_revision"] != "jev-latest"
            or policy["token_counter_revision"] != "utf8-bytes-upper-bound-v1"
        ):
            raise ContractError("unsupported judgment model or token counter revision")
        if len(candidates) > min(policy["max_calls"], policy["max_candidates"]):
            raise ContractError("judgment call budget exceeded")
        offered = [row["candidate_id"] for row in candidates]
        if len(set(offered)) != len(offered):
            raise ContractError("duplicate judgment candidate")
        wires = [
            candidate_request_shape(task, json.dumps(dict(row), sort_keys=True))
            for row in candidates
        ]
        token_bound = sum(len(wire.encode()) for wire in wires)
        if token_bound > policy["max_input_tokens"]:
            raise ContractError("judgment context budget exceeded")
        rates, ceiling = policy["rates"], policy["spending_ceiling"]
        if ceiling is not None:
            if (
                rates is None
                or rates["input_rate"] is None
                or rates["output_rate"] is None
                or rates["currency"] != ceiling["currency"]
            ):
                raise ContractError("unknown judgment cost")
            if Decimal(rates["output_rate"]) > 0:
                raise ContractError("provider output spend bound unavailable")
            estimate = Decimal(token_bound) * Decimal(rates["input_rate"]) + Decimal(
                policy["max_output_tokens"]
            ) * Decimal(rates["output_rate"]) * len(candidates)
            if estimate > Decimal(ceiling["amount"]):
                raise ContractError("judgment spend budget exceeded")
        results: dict[str, bool] = {}
        measurements: dict[str, list[dict[str, Any]]] = {}

        def observer(invocation_id: str) -> Callable[[object], None]:
            previous: JevUsageObservation | None = None
```

## Source excerpt: scripts/verify_route_phase.py:20

```
PROOF_TIMEOUT_SECONDS = 600
MATRIX = {("Linux", "3.13"), ("Darwin", "3.13"), ("Windows", "3.13")}
CHECKS = {
    "tests",
    "contracts",
    "generation",
    "vocabulary",
    "imports",
    "lint",
    "format",
    "types",
    "build",
    "cli",
    "vocabulary_lint",
    "installed_package",
    "cold_cli",
}
REQUIREMENTS = {f"EC-ROUTE-{number}" for number in range(1, 5)} | {"IF-0-VC-2"}
REQUIRED_TEST_PATHS = (
    "tests/costing",
    "tests/guidance",
    "tests/privacy/test_storage_privacy.py",
    "tests/privacy/test_context_privacy.py",
    "tests/privacy/test_jev_privacy.py",
    "tests/privacy/test_application_privacy.py",
)


def command_digest(command: list[str]) -> str:
    return hashlib.sha256(json.dumps(command, separators=(",", ":")).encode()).hexdigest()


def commands_for(python: str, temporary: Path, os_name: str | None = None) -> dict[str, list[str]]:
    scoped_checks = [
```

## Reconciliation since prior review



The owner approved one focused confirmation round after the original cap,
using Gemini, Grok and Astra as reviewers and Astra as president. This is an
explicit board change, not a silent fallback or a waiver of substantive findings.

Base: the round-3 frozen bundle and individual verdicts. Current plan changes:

- Only selected_guidance and no_optional_guidance may feed route-v2, including
  cache/retry/commit paths. Test every result variant with an otherwise feasible
  quality-sufficient candidate. Preserve uncertainty and termination metadata.
- Preferred and deferred queues are FIFO by monotonic enqueue sequence. Stable
  IDs order siblings at insertion. Alternate nonempty queues; retain excess
  frontier options as requeued cursors. No last-service re-sort remains.
- Define stricter constraints field by field, including the existing v1 meaning
  of an empty allowed_providers list. Reject relaxations/incomparable changes.
- Recovery of a nonterminal attempt never dispatches additional provider work.
  It reduces durable observations or returns interrupted failure; a new response
  deadline does not reset the original provider allowance.

Confirm these repairs and identify only concrete remaining EC/contract defects.
Implementation artifacts are future obligations, not evidence already produced.
