---
phase_loop_plan_version: 1
phase: ROUTE
roadmap: specs/phase-plans-v1.md
roadmap_sha256: 4ecbf27188b634d6ea5346cd67d61ab36d50d3ad0416a9a6d0d2602bb2698ab8
---

# ROUTE: Durable routing core

> Review status: owner-authorized confirmation completed with Gemini, Grok and
> Astra, chaired by Astra. The chair's two required storage clarifications are
> incorporated below and approved in the owner's requested Codex self-review.
> This is not unanimous panel approval. See phase-plan-v1-ROUTE_reviews.md.

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
"ObserveDiscoveryOption-v1"; preserve historical JudgeCandidate-v1 parsing/replay.
The owner-approved October 12 amendment authorizes JudgeCandidate-v2 for new calls
and template/projection bindings; see
`evidence/EXPERIMENT/fix-review-20261011/round-3/version-amendment.json`. Shared
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
Each scoped idempotency key owns an independent append-only ledger with an
immutable initial allowance from its own fresh limit intersection. A new key
neither shares nor inherits another attempt's remaining calls/tokens/spend and
cannot clear its reservations. Same-key recovery never increases the original
allowance; current authority restrictions can only narrow what remains permitted.
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
Recovery rechecks the parent tombstone and atomically commits its terminal result,
including interrupted failure, before returning. An observation may affect the
result only while the attempt is nonterminal, in a transaction that rechecks the
tombstone and status. After terminalization, late observations are audit-only,
subject to privacy/deletion rules: they cannot replace the result, restore a
route allowlist or release reserved allowance. Concurrent recoveries return the
same committed result. Test recovery versus late observation and deletion races,
plus independent new-key limits and unchanged same-key limits after a crash.

## Lane Index & Dependencies

- SL-0 — Contracts and vocabulary; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 — Pure navigation; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 — Bounded judgment and persistence; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 — Application and CLI; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 — Verification and handoff reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: (none); Parallel-safe: no

## Lanes

### SL-0 — Contracts and vocabulary

- **Scope**: Freeze additive discovery/link contracts, canonical names and strict validation.
- **Owned files**: `baml_src/**`, `src/baml_sdk/**`, `schemas/**`, `src/jevdrill/contracts.py`, `docs/vocabulary.yaml`, `docs/vocabulary.md`, `docs/contracts.md`, `docs/route-interfaces.md`, `tests/contracts/**`, `scripts/contract_consumer.mjs`, `scripts/check_generated_contracts.py`, `pyproject.toml`, `uv.lock`, `.phase-loop-generated-outputs.json`, `.github/workflows/route.yml`, `src/jevdrill/BAML_TYPESAFE_LICENSE`, `src/jevdrill/BAML_TYPESAFE_NOTICE.md`, `src/jevdrill/context.py`, `src/jevdrill/costing.py`, `src/jevdrill/guidance.py`, `src/jevdrill/inventory.py`, `src/jevdrill/routing.py`, `src/jevdrill/settings.py`, `src/jevdrill/telemetry.py`, `src/jevdrill/integrations/__init__.py`, `tests/context/**`, `tests/costing/**`, `tests/guidance/**`, `tests/inventory/**`, `tests/routing/**`, `tests/settings/**`, `tests/privacy/test_context_privacy.py`, `tests/privacy/test_jev_privacy.py`, `tests/privacy/test_storage_privacy.py`
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
  - test: Loopback transport exercises generated ObserveDiscoveryOption and partial usage; inject invalid binding, timeout, missing usage, crash after reservation, duplicate/conflicting keys and deletion races. Prove atomic terminal recovery, audit-only observations after terminalization, independent new-key ledgers and non-replenishing same-key recovery.
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

October 8 execution preflight: planning-only main does not contain the routing
baseline described above. Recover public ROUTE source and synthetic tests from
the committed `9a1a94f81` tree into an isolated feature worktree; recover only the
pinned TypeSafe patch, attribution, usage projection and parity tests from the
preserved `codex/v0-linux` worktree. Its unfinished HOST/LEARN/EXPERIMENT code
and all research inputs remain untouched. SL-0 additionally owns the baseline
bootstrap paths and generation script listed above; other recovered files stay
in their existing owning lanes. No dependency version change is authorized.
Read allowlist: `.baml/**` compiler/toolchain metadata and executables only,
excluding profiles and payloads. Generated outputs are regenerated normally.
SL-0 also owns `tests/conftest.py` for shared synthetic fixtures. A baseline
verification found that the planning merge changed six CONTRACT coverage source
bindings (including JD-083/084). SL-0 may reconcile only
`evidence/CONTRACT/coverage.json` source bindings and mapping entries, retaining
the original bytes under `evidence/ROUTE/history/`; platform reports and every
other CONTRACT evidence file remain read-only. This refresh claims no CONTRACT
gate and changes no accepted product decision.
SL-0 may also recover `research/evaluation/cases.json`, the committed public
synthetic development fixture required by the retained catalog checks. This
exact path is an allowed read input; no other research corpus or holdout is
authorized. It remains synthetic regression evidence, not quality evidence.

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
