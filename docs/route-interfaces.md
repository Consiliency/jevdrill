# ROUTE interfaces

ROUTE keeps external effects behind the protocols in `jevdrill.contracts`. Every
method receives an immutable, already-validated input. `scope` contains the
project, workspace, producer, and operation identities; project identity is
stable across moves while workspaces isolate execution.

| Port | Frozen method | Contract |
|---|---|---|
| `StoragePort` | `commit_decision(scope, key, digest, bundle)` | Persist an immutable decision before returning a ready result. |
| `StoragePort` | `ingest_report(scope, key, digest, event)` | Durably append or acknowledge one immutable event. |
| `StoragePort` | `load_replay(scope, decision_id)` | Return recorded routing material without a provider call. |
| `StoragePort` | `delete_task(scope, task_id)` | Remove task material and leave a tombstone that prevents resurrection. |
| `InventoryPort` | `snapshot(target, deadline)` | Return a fresh validated inventory snapshot before the shared deadline. |
| `TokenCounter` | `count(text, model_revision)` | Count complete routed text against the exact selected revision. |
| `JudgmentPort` | `judge(task, candidates, deadline)` | Judge only offered candidates before the shared deadline. |

Database and provider effects do not enter pure routing. Missing values remain
explicit in the BAML contracts; adapters must not invent a readiness result.

`RouteInputs` supplies a frozen `RouteRequest` with separately validated
`InventorySnapshot`, `CatalogSnapshot`, ordered `SettingsLayer` inputs and an
optional `JudgmentPolicy`. A bare version-1 request supplies no inventory and
cannot establish model availability. Capability strings are permissions, never
model identities. Every candidate binds a resolved revision, access route,
freshness, native effort, token-counter revision, quality evidence and nullable
rates. Unknown rates and quality remain unknown.

`InspectRequest`, `DeleteRequest` and `CommandScope` validate management inputs.
`ReplayBundle` retains the validated response, request/cache digests and optional
`JudgmentRecord`; replay does not call a provider. Request idempotency is scoped
by project/workspace/producer/operation. Task deletion spans every producer and
operation within the same project/workspace.

`RouteInputs.completion_time_limit_ms` is an explicitly omittable, nullable
execution-time ceiling, separate from the routing deadline. The CLI accepts
`--remaining-budget-ms` and starts its local timer before heavyweight imports.
Hosts must account for spawn time and enforce the output bounds advertised in
their inventory when they execute a selected plan.

The inspected `phase-loop-runtime` version is 0.7.19. Its
`capability_registry()`, `ExecutorCapabilityRecord`, `auth_ok_for()` and
`LaunchRequest` describe executor eligibility and dispatch inputs. These are
not model-availability evidence. ROUTE accepts an explicit host-produced
`InventorySnapshot` with source version, requested model ID, resolved revision,
route, effort and freshness; it never translates an executor name into a model.
No synchronous authentication scan runs on the routing path.

## Discovery and linked tasks

`Application.discover(DiscoveryInputs, deadline)` owns successive questions and
state advancement. Discovery has its own envelope, policy and management scope
with operation `discover`. `work_objective_id` identifies the work lifecycle;
the optimization metric's `objective_id` remains separate. It requires no model
inventory. Descriptions bind resource/revision/content hash plus their own
revision and digest; absent or oversized descriptions remain unknown. The
default description limit is 2,048 UTF-8 bytes and settings may only reduce it.

| Discovery status | Meaning | Eligible for route-v2 |
| --- | --- | --- |
| `selected_guidance` | Supported feasible optional guidance; incomplete search retains uncertainty | Yes |
| `no_optional_guidance` | Complete search with no feasible supported optional resource | Yes |
| `needs_context` | Missing authorized input takes precedence | No |
| `constraint_conflict` | Required guidance is missing, conflicting or cannot fit | No |
| `discovery_failed` | Incomplete search without supported feasible guidance | No |

`next_question` offers stable option IDs at domain, specialty, task-family and
resource levels. `apply_answers` requires the current question digest. Category
answers steer alternating preferred/deferred FIFO queues; false answers defer
children without permanently excluding them. Cursors enforce active width;
visited IDs and finite rounds/candidates prevent repetition. Only resource
judgments support suitability. Exact IDs and aliases can bypass taxonomy levels
but retain admission and suitability checks. Discovery never calls `narrow`.

`ObserveDiscoveryOption-v1` uses the pinned observation patch independently of
`JudgeCandidate-v2`. Provider submission for discovery contains sanitized authorized objective,
context, question level/digest, option ID and compact description or explicit
unknown. Instruction bodies, source/rights records and arbitrary catalog fields
stay local. The durable ledger reserves each call and conservative input bound
before dispatch, counts failures and never releases unknown usage. Output
planning reservations are not hard output limits. Requested hard output limits
reject; spending ceilings require verified input pricing with zero output rate.
Unknown prices stay unknown. Every invocation retains the five-second deadline
and a commit margin of at least 50 ms.

The owner-approved judgment amendment uses `JudgeCandidate-v2` for new task
suitability calls. Historical v1 policies and records remain parseable for stored
inspection and replay; an active v1 policy cannot dispatch the current template.
Task suitability sends authorized task, acceptance, context and governing references,
plus the selected model/effort/limits and exact required and optional instruction
bodies. It omits unselected option menus and internal pricing metadata. The named
projection includes verification timestamps; those continue to distinguish receipt
identity. Rendered template digests and the projection version/fields bind the
development judge configuration, study validator and route cache. Same-key replay
returns the immutable stored result; a new request cannot reuse an earlier template's
cache entry. Legacy development worker profiles are retained for inspection, not
reopened for new calls.

`DiscoveryRouteInputs` has schema version `2`, nested unchanged v1 `route_inputs`
and `discovery_ref` containing discovery ID, work objective ID and trace digest.
Only an authorized stored successful result may feed selection. Scope, tombstone,
catalog revisions and exact content digest are checked before preparation or
retry reuse, and linkage is checked again inside the route commit transaction.
Nested `catalog_query` must be null or absent. Fresh candidate guidance options
are intersected with discovered triples and rebound to the concrete task while
preserving admission, authority and roles. All zero/one/two combinations remain.
Mandatory references coalesce only when revision/hash/role/authority/admission
match; instructions are retrieved and counted again for each candidate.

Task constraints may only tighten: time/context/attempt and execution token
limits decrease, provider restrictions shrink without becoming unrestricted,
local-only can become true, governing references grow, and existing spending
caps decrease in the same currency. Excluded paths are unioned; acceptance
requirements remain unchanged by ID, with additions allowed. Requested execution
spending/token ceilings require verified whole-run limits, not planning estimates.
Linked decisions retain discovery identity, termination and uncertainty. A
reference grants no execution permission or fallback authority.

`inspect-discovery --discovery-id ID --scope JSON [--replay]` reconstructs
transitions and deterministic selection from recorded IDs, answers, admission,
compatibility/context facts and budget deltas, without provider traffic or the
live catalog. Raw objective/context/description retention is opt-in. Erased
payloads are never reconstructed. Cache/idempotency identity binds sanitized
context, descriptions, taxonomy/catalog/content, policy/function/model, scope
and authorization; route-v1 digest construction is unchanged.

`delete-discovery --work-objective-id ID --scope JSON` permanently tombstones the
project/workspace/discover objective across authorized producers. Each scoped
idempotency key has an independent fixed allowance and immutable discovery ID.
Same-key recovery dispatches no new provider calls: it atomically reduces durable
observations to partial supported guidance or interrupted failure. Concurrent
recoveries return the same result. Late observations are audit-only and cannot
replace a terminal result or restore an allowlist. Deletion invalidates all
attempts, retry/cache responses, replay and future linked route commits; task
records retain their separate deletion scopes.
