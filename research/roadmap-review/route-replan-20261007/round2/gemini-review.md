# Implementation Readiness Review: ROUTE Phase Plan (`phase-plan-v1-ROUTE.md`)

## 1. Executive Summary and Adjudication

The proposed plan (`plans/phase-plan-v1-ROUTE.md`, Round 2) provides a rigorous, implementation-ready architecture that directly resolves the gaps identified in `docs/drill-roadmap-map.md` and the Round 1 review. It cleanly introduces application-owned progressive navigation (`EC-ROUTE-5`, `EC-ROUTE-6`) while preserving existing v1 catalog admission, deterministic ranking, conservative token counting, and configuration selection in `src/jevdrill/application.py` (`EC-ROUTE-1`–`EC-ROUTE-4`, `EC-ROUTE-7`).

The division of responsibility between ROUTE and HOST is strictly maintained: ROUTE establishes and proves the public discovery and linked task routing boundary (`discover` → `route-v2`) via synthetic fixtures, while HOST retains ownership of actual task decomposition and harness execution.

There are no unresolved blockers. The plan is **implementable as specified**.

---

## 2. Implementability and Existing Selector Reuse

- **Selector Preservation (`src/jevdrill/application.py`)**: The plan preserves `_prepare` and `select_plan` without modifying the core combinatorial evaluation of guidance options (zero, one, or two optional resources) or native effort / model / route feasibility checks.
- **Conversion Boundary**: Route v2 (`DiscoveryRouteInputs`) adapts discovery results before entering `_prepare` by:
  1. Intersecting discovered guidance resource triples `(resource_id, revision, content_hash)` with candidate `guidance_options`.
  2. Rebinding the task-specific `task_id` onto matched `GuidanceRevision` rows to satisfy the existing invariant in `_prepare` (`guidance["task_id"] != request["task_id"]`).
  3. Re-evaluating context limits, conflict sets, and admission rules against the fresh task constraints.
- **Sequential Lane Disjointness**: The 5 sequential lanes (SL-0 to SL-4) have disjoint file ownership:
  - `SL-0`: Contracts, BAML sources, schemas, vocabulary (`baml_src/**`, `src/baml_sdk/**`, `schemas/**`, `src/jevdrill/contracts.py`, `docs/*`, `tests/contracts/**`).
  - `SL-1`: Pure navigation (`src/jevdrill/discovery.py`, `src/jevdrill/catalog.py`, `tests/discovery/**`, `tests/catalog/**`).
  - `SL-2`: Bounded judgment and storage (`src/jevdrill/integrations/jev.py`, `src/jevdrill/storage.py`, `tests/integrations/**`, `tests/storage/**`, `tests/privacy/test_discovery_privacy.py`).
  - `SL-3`: Application and CLI (`src/jevdrill/application.py`, `src/jevdrill/cli.py`, `tests/application/**`, `tests/cli/**`, `tests/privacy/test_application_privacy.py`).
  - `SL-4`: Verification and handoff reducer (`scripts/verify_route_phase.py`, `tests/verification/**`, `evidence/ROUTE/**`, status docs).
  This enforces zero file overlap and eliminates parallel collision risk.

---

## 3. Contract Compatibility and Boundaries (`EC-ROUTE-5`)

- **Additive Specification Amendment**: In accordance with the roadmap closeout policy (`canonical_spec_update`, schema `spec_delta_closeout.v1`), discovery contracts and `route-v2` wrappers are added without mutating existing v1 contract validation or fixtures.
- **Identity Disambiguation**:
  - `work_objective_id` is dedicated to the lifecycle of work/discovery, leaving `OptimizationObjective.objective_id` untouched for optimization metrics.
  - Discovery lifecycle and tombstones use dedicated `DiscoveryScope`, `DiscoveryInspectRequest`, and `DiscoveryDeleteRequest` with `operation: "discover"`, preventing schema pollution of `CommandScope` (`operation: "route" | "report"`).
- **Separation of Policy and Observation**:
  - Preserves `JudgeCandidate-v1` and candidate suitability contracts intact.
  - Adds `ObserveDiscoveryOption-v1` with `DiscoveryJudgmentPolicy` and `DiscoveryJudgmentRecord`, preventing cross-pollution between candidate evaluation and option navigation.
- **Decoupled Catalog Descriptions**:
  - Rather than mutating `CatalogResource` in `baml_src/contracts.baml` (which lacks a description field), descriptions are supplied via versioned `DiscoveryDescription` records linked by `(resource_id, revision, content_hash)`. Catalogs lacking descriptions treat them as explicit unknowns rather than attempting unsafe lexical inference.

---

## 4. Search, Navigation, and Termination (`EC-ROUTE-6`)

- **Application-Owned Transitions (`src/jevdrill/discovery.py`)**:
  - State machine advances `domain → specialty → task_family → resource leaf` through `next_question(state)` and `apply_answers(state, answers)`.
  - Question options are cryptographically bound to a question digest over state and offered options; unknown, duplicate, or stale option responses fail contract validation.
- **Avoidance of Starvation & Traversal Traps**:
  - Eliminates dependency on `catalog.narrow` during progressive discovery.
  - Implements least-recently-served traversal with deferred queues, retaining alternative branches across domains when classification is ambiguous.
  - Exact shortcuts on resource ID/revision or unique alias bypass taxonomy levels but are strictly subjected to admission and suitability validation.
- **Termination Soundness**:
  - Distinct terminal states: `selected_guidance`, `no_optional_guidance`, `needs_context`, `constraint_conflict`, `discovery_failed`.
  - Incomplete searches due to budget exhaustion return supported leaves with explicit uncertainty or return `discovery_failed`. They cannot return `no_optional_guidance`.
  - Unknown provider answers prevent a complete-negative conclusion.

---

## 5. Privacy and Trace Replay Integrity (`EC-ROUTE-4`, `EC-ROUTE-5`)

- **Provider Payload Allowlist**:
  - Outbound JEV payload is strictly limited to authorized sanitized context, question digest, and option identifiers/descriptions.
  - Instruction texts, reuse rights, source occurrences, and internal catalog metadata are never dispatched to provider endpoints.
- **Text-Free Trace Replay**:
  - `DiscoveryTrace` records topological transitions, offered IDs, bound Boolean answers, evidence digests, and budget deltas.
  - Trace replay reconstructs search paths deterministically from recorded transition facts without invoking provider APIs or regenerating raw prompts.
  - If raw text retention is opted out or privacy restrictions forbid retaining facts, replay is reported as unavailable rather than fabricated.

---

## 6. Crash Consistency, Idempotency, and Lifecycle (`EC-ROUTE-1`, `EC-ROUTE-4`)

- **Atomic Reservation & Scoped Keys**:
  - Discovery IDs are minted once in durable storage, keyed by envelope idempotency key and scoped request digest.
  - Payloads with matching idempotency keys but altered request digests trigger contract conflict errors.
- **Transactional Linkage**:
  - Verification of linked discovery validity (checking for tombstones/deletions) and route decision commitment occur within a single database transaction, eliminating TOCTOU race conditions.
  - Provider calls remain strictly outside database transaction boundaries.
- **Budget Retention Across Interruptions**:
  - Call reservations are committed before dispatch; interrupted attempts either resume from recorded observations or terminate with explicit failure, preventing silent retry budget leaks.

---

## 7. Deadline and Budget Accounting (`EC-ROUTE-3`, `EC-ROUTE-6`)

- **Hard Deadline Containment**:
  - Discovery operates under the mandatory 5.0-second CLI request deadline, reserving at least the existing 50 ms commit margin for durable write-out.
- **Strict Budget Ledger**:
  - Enforces explicit ceilings on rounds, active width, examined candidates, provider calls, input/output tokens, and financial cost.
  - Rejects positive output-rate spending bounds when the underlying adapter cannot guarantee bounded output tokens for Boolean responses (preserving the invariant in `src/jevdrill/integrations/jev.py:60`).
  - Employs conservative token bounds without conflating packing estimates with measured usage.

---

## 8. Verification Reducer and Acceptance Falsifiers (`IF-0-VC-2`, `EC-ROUTE-1`–`7`)

- **Matrix and Control Integrity**:
  - `scripts/verify_route_phase.py` is explicitly extended from 4 to 7 criteria (`EC-ROUTE-1` through `EC-ROUTE-7` plus `IF-0-VC-2`).
  - Rejects legacy manifests missing new criteria, tests, or negative controls.
  - Matrix validation spans Linux, Darwin, and Windows under Python 3.13.
- **Concrete Acceptance Falsifiers**:
  - Each criterion is bounded by explicit falsification conditions (e.g., admitting known-unsuitable controls, bypassing discovery with preselected options, dropping recoverable alternate branches, or unrecorded success escaping after deadline expiry).

---

## 9. Missing Evidence and Non-Blocking Suggestions

### Missing Evidence (Appropriately Deferred to Implementation)
As required for pre-implementation plan review, the following are not yet present and are planned deliverables under SL-0 through SL-4:
1. Compiled BAML artifacts for `ObserveDiscoveryOption` in `src/baml_sdk/`.
2. Migration files and schema definitions for discovery reservations and traces in `src/jevdrill/storage.py`.
3. Native execution test artifacts under `evidence/ROUTE/` across Linux, macOS, and Windows.

### Non-Blocking Suggestions
1. *Deterministic Leaf Selection*: When multiple leaf candidates satisfy suitability and context constraints within the two-resource optional budget, ensure the tie-breaking rules explicitly order candidate combinations by `(len(combo), resource_id_1, revision_1, resource_id_2, revision_2)` to prevent nondeterministic permutations across platforms.
2. *Granular SQLite Lock Busy Handling*: When checking discovery deletion tombstones during concurrent task routing in `SL-2`/`SL-3`, ensure SQLite `busy_timeout` is configured to avoid transient `sqlite3.OperationalError` false-positives under high concurrency within the 50 ms commit window.

---

AGREE
