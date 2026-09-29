# JEV Drill: implementation proposal

Status: proposed implementation detail for brownfield intake, not adopted canonical output.
Authority: [accepted decisions](jevdrill-design-input.md) take precedence. This proposal makes implementation choices concrete without representing every detail as user-approved. CONTRACT now implements draft BAML contracts, strict boundaries and offline client tests. Contract freeze and the production router/host adapter remain pending.

## 1. Source and package layout

```text
specs/
  jevdrill-design-input.md          accepted decisions and supersession
  jevdrill-current-state.md         inspected code, gaps, and evidence
  jevdrill-implementation-proposal.md
docs/
  jevdrill-spec.md                  preserved original product draft
  vocabulary.yaml                  vocabulary machine authority
  vocabulary.md                    generated glossary, never hand-edited
src/jevdrill/
  contracts.py                     generated type facade and explicit validators
  settings.py
  catalog.py
  inventory.py
  context.py
  routing.py
  guidance.py
  costing.py
  evaluation.py
  analysis.py
  experiments.py
  telemetry.py
  storage.py
  application.py
  cli.py
  integrations/
    jev.py                         BAML boundary and result conversion
baml_src/
  contracts.baml                   authored public data contracts
  jev.baml                         JEV-compatible judgment functions/types
schemas/                           generated public JSON Schema
tests/                             modules follow application responsibility names
scripts/                           existing research tools remain separate
research/                          existing evidence remains explicitly unvalidated
```

The BAML source location is a proposal subject to the pinned v1 toolchain's packaging convention. Put generated types/bindings in a declared generated package; exclude its provider/runtime dependencies from the pure public-contract import path where the generator permits. Prove that this separation works rather than copying generated fields into handwritten types. Generated artifacts require a reproducible build step. Do not copy agent-harness's v0 BAML syntax or dependency pin into this package. The later `objectives` module is not required for stage 1; objective records are.

CONTRACT selects CPython 3.13 with locked Pydantic 2 and BAML compiler/bridge 0.20.1. Linux/macOS/Windows support requires actual matrix results. Generated code lives in `src/baml_sdk` because the pinned compiler hardcodes that import namespace. Public contracts currently require the bridge. The enforced dependency graph is in `docs/vocabulary.yaml`, including explicit generated-package exceptions for contracts and telemetry. SQLite and platform-path selection remain ROUTE work.

## 2. Dependency direction

Application imports are limited to this proposed acyclic graph; standard-library and approved third-party imports are outside this table. `contracts` owns interfaces for effectful dependencies. Pure modules receive validated snapshots rather than opening databases or contacting providers.

| Module | Permitted direct application imports |
|---|---|
| `contracts` | none |
| `settings`, `inventory`, `context`, `catalog` | `contracts` |
| `costing`, `guidance`, `telemetry` | `contracts` |
| `routing` | `contracts`, `costing` |
| `evaluation` | `contracts` |
| `analysis` | `contracts`, `evaluation` |
| `experiments` | `contracts`, `evaluation`, `costing` |
| `storage`, `integrations` | `contracts` |
| `application` | all modules above |
| `cli` | `application`, `contracts` |

`experiments` owns orchestration rules and calls injected execution interfaces; concrete provider effects stay in `integrations`, and `application` supplies the implementations. `settings` may read explicitly selected local configuration files but never execute their contents. Any later dependency change updates the graph and tests deliberately.

## 3. BAML/JEV boundary

Accepted requirements: JD-081 and JD-082. BAML is the preferred authored source for both public data types and internal model-call types where supported. Generate Pydantic and required other-language types; verify the JSON Schema export path. Convert JEV results to validated judgment records before deterministic selection. General BAML types can be broader than types supported by the JEV client: do not pass the entire public routing decision as a JEV function's return type.

Initial compatibility-test pin: [`baml-language-0.20.1`](https://github.com/BoundaryML/baml/releases/tag/baml-language-0.20.1), published September 20, 2026. This newer BAML v1 language toolchain uses a `0.x` release number. Its tagged source contains [JEV request/response tests](https://github.com/BoundaryML/baml/blob/baml-language-0.20.1/baml_language/crates/baml_tests/baml_src/ns_llm_typesafeai_examples/examples.baml), a [Pydantic 2 class emitter](https://github.com/BoundaryML/baml/blob/baml-language-0.20.1/baml_language/sdks/python/rust/sdkgen_python_pydantic2/src/emit/class.rs), and the [Python runtime bridge](https://github.com/BoundaryML/baml/blob/baml-language-0.20.1/baml_language/sdks/python/README.md). Use this exact release for the first proof; record artifact checksums and compatible Python bridge/dependency versions. Use version-matched language guidance. Any pin change requires an explicit recorded reason and rerunning the compatibility proof, rather than following a moving canary/nightly target.

The legacy installation remains `0.226.2`. An isolated, checksum-verified `0.20.1` toolchain and matching Python bridge now pass generation, five status-variant roundtrips, JSON Schema export, credential-free request construction, local mock decoding, and a request-timeout check. One authorized live JEV call also succeeded. See the [reproducible compatibility proof](../research/baml-proof/README.md) for versions, commands, observations, and limitations.

The proof found that generated Pydantic models ignore unknown fields, coerce numeric strings, and make nullable fields omittable. Implement and verify a deterministic strict validation/export layer derived from BAML before contract freeze. The generated package also initializes the runtime on import; prove a runtime-free contract path or explicitly document the bridge dependency. Live token counts arrived in a separate `Usage` event while `LLMCall.usage` was null; preserve this source distinction in the telemetry adapter. These findings qualify the pin for continued implementation, not unconditional contract adoption.

Before schema freeze, generate all five response variants and test strict unknown-field rejection, required-versus-nullable fields, literal discriminators, enum serialization, aliases, numeric coercion, nested models, extension values, JSON Schema export, and cross-language fixtures. If generated defaults are permissive, enforce boundary rules through a deterministic schema/validation layer derived from the same definitions, plus explicitly named semantic validators. Do not edit generated code or maintain a second handwritten field catalog. Cross-field and semantic validation remains necessary even with BAML-authored types.

Verified documentation constraints: the announced client targets BAML v1; boolean/float outputs are binary judgments/probabilities, finite choices and fixed-field classes are supported, while free-form outputs and collection-shaped returns are restricted. It does not expose JEV's Score primitive. Choice confidence is not a new float field: that would ask another independent question. Usage is exposed through events; wire bodies require deliberate privacy handling. [BoundaryML announcement](https://boundaryml.com/blog/typesafe-ai-jev).

Proposed implementation:

- Put question definitions, finite response choices, and descriptions in authored BAML sources. Keep task/catalog text as data rather than interpolating it into executable BAML source.
- Start with fixed-shape per-candidate suitability judgments. Consider bounded pairwise comparisons using fixed choice labels mapped to recorded candidate IDs. Do not assume runtime-sized candidate arrays are supported return types.
- Preserve raw provider probability as an uncalibrated judgment; code owns the policy threshold. Do not interpret a probability as a numeric cost, quality score, or guaranteed success rate.
- Validate proposed judgments against offered candidates and pinned request schema. Cross-field consistency checks stay in Python because independent judgments may disagree.
- Explicitly disable full wire-body capture in normal operation. Extract permitted structured usage/judgments through the supported event interface; never log credentials or full task payloads incidentally.
- Use the remaining routing deadline for the BAML call, without nested retries that reset the deadline. Provider failure uses the accepted deterministic fallback.
- Record toolchain version, function source digest, requested JEV alias/version, resolved version if observable, judgment schema version, and usage source. Unknown resolution remains unknown.

The JEV implementation originated in [BoundaryML/baml#4938](https://github.com/BoundaryML/baml/pull/4938) and is present in the selected release. It supports finite-choice counts of 2–255 and validates unsupported shapes before HTTP. Basic local runtime and Python interoperability are demonstrated; complete contract, cancellation, and event privacy checks remain verification obligations.

Required compatibility proof before integration freeze: use the pinned `baml-language-0.20.1` toolchain to generate the public contracts and compile representative JEV functions in the same proof. Verify the strict validation and schema-export cases above, build requests without credentials, exercise Python interoperation or a BAML CLI bridge, check timeout/cancellation and usage capture, and run privacy-safe mocked response cases. Record exact commands, versions, generated artifacts, and outcomes. Prefer supported in-process Python calls if available; otherwise use an isolated BAML process behind the same adapter and measure startup. Adoption requires these checks to pass together. This is a technical spike, not another product question or permission to bypass BAML.

## 4. Verified agent-harness integration points

Inspected local agent-harness revision `b9627d538faad872077472e3711a941198add5da`. All paths below are relative to that repository; no sibling files were changed.

| Surface | Inspected code | Proposed use and limit |
|---|---|---|
| Capability declarations | `phase-loop-runtime/src/phase_loop_runtime/capability_registry.py`, `models.py:ExecutorCapabilityRecord` | Translate action support, injection mode, permission posture, proof gates, and route constraints; declaration is not live model verification |
| Availability/auth | `executor_availability.py`, `default_executor_resolver.py` | Preserve existing eligibility gates; do not replace them with a recommendation |
| Launch input | `models.py:LaunchRequest`, `launcher.py:build_launch_request` | Apply only validated selectable model/effort and compatible guidance before launch construction |
| Launch validation | `launcher.py:build_launch_spec`, `LaunchSpec` | Recheck and report selected/requested/effective values; preserve route restrictions and authorization |
| Execution | `launcher.py:launch_with_spec`, called from `runner.py` | Attach run identity, report actual application and completion; dry runs never become real success evidence |
| Completion/metrics | `observability.py:build_work_unit_metric`, `append_work_unit_metric`, terminal summaries | Map permitted fields to execution events and queue durably; terminal return does not always mean accepted task completion |

The registry includes codex, claude, gemini, grok, opencode, pi, command, and manual entries. Eligibility varies by action, launch mode, proof/promotion, authentication, and host. This list is not an assertion that every route is verified or available now. `command` and `manual` do not automatically provide executable model plans.

`WorkUnitMetric` currently carries model/effort, fallback, duration, return code and terminal/verification status, but no input/output token or monetary-cost fields. Its model metadata can come from selection rather than provider confirmation. Export with attribution, not as verified observed model identity. Native effort must not be reconstructed from normalized labels without route evidence. Add a versioned bridge and provider-usage extraction where supported; use unknowns otherwise.

Existing auth probes can take ten seconds each, exceeding the five-second route budget. Prefer pre-refreshed bounded snapshots; do not run unrestricted synchronous auth scans on the routing path. Some inspected convergence execution primitives use Unix process-group operations. Cross-platform adapter behavior needs explicit tests rather than inherited support claims.

No existing JEV bridge was established by the inspected runtime searches. Proposed integration is additive: one bridge used by relevant runner paths, not an independent replacement launcher. Include main dispatch and delegated/lane execution in coverage. Preserve governing execution-policy overrides, Claude route restrictions, and existing permission decisions.

## 5. Portable contract families

Proposed exact spellings below are implementation candidates. Once frozen, add them to the vocabulary registry. Do not maintain these tables as a second schema after BAML generation exists.

### Common envelope

`schema_version`, `request_id`, `operation`, `project_id`, `workspace_id`, `harness_id`, `execution_target_id`, `created_at`, `extensions`. Mutating operations additionally require `idempotency_key`. Use UUID strings for opaque identities, RFC 3339 UTC timestamps, milliseconds for durations, and decimal strings plus currency for money. Reject nonfinite numbers and silently coerced scalar types. Unknown measurements use a tagged representation with a missing reason, not zero or unexplained null.

### Route request

Required: task identity and representation, acceptance requirements, optimization objective/cost basis, hard constraints, active guidance, governing-instruction references, declared/runtime capabilities, inventory/context/settings revisions, execution mode, deadline, and recursion-bypass marker. A nullable field is not a substitute for deciding whether absence means default, unknown, or not applicable.

Response common fields: decision/request/task IDs, creation time, status, diagnostics, objective, evidence references, version references, and cache-reuse provenance. Status-specific fields:

| Status | Required | Forbidden |
|---|---|---|
| `ready` | selected immutable plan, readiness evidence, guidance action, validity conditions | unresolved required prerequisites |
| `needs_context` | missing facts and why each matters | selected executable plan |
| `constraint_conflict` | conflicting constraints and their authorities | selected executable plan |
| `no_compatible_plan` | candidate exclusion reasons and feasible setup proposals if any | selected executable plan |
| `routing_failed` | typed error code, retryability, permitted diagnostic | selected executable plan |

Readiness is not success, delivery, capacity reservation, or execution authorization. Reusing a decision returns its original validity conditions and links the new request; it does not renew stale checks. Setup and preferred-but-unapplied alternatives are separate fields.

### Execution plan

Plan ID and hash; model ID and optional resolved revision; provider/access route; native effort union (`explicit`, `provider_default`, `unsupported`); exact guidance revisions and order; required capabilities; target/harness requirements. Bind ordered content hashes. No-skill plans use an explicit `none` action and empty optional guidance; they still have a model and effort state.

Store delivery/application outside the immutable plan. A later changed plan has a new ID and links its predecessor with a substitution reason. The host validates readiness again before execution.

### Events and measurements

Propose one immutable event envelope with `event_id`, `event_type`, scope, decision/plan/run references, `source_id`, source sequence, occurrence/receipt timestamps, schema revision, payload, and optional `supersedes_event_id`.

Start with queued, started, plan-applied, usage-reported, completed, failed, canceled, evaluation-reported, host-choice-reported, and correction events. Completion is process/work completion, not necessarily acceptance. Treat evaluation and preference as independent records. Partial/out-of-order events are stored with join status; deterministic projection must not regress a terminal run on receipt of an older started event. Corrections identify an original event and never erase it.

Every measurement records metric definition/version, value/unit or missing reason, source, method, scope (call/run/task/experiment), and estimate/observed posture. Define missing reasons for unsupported, not reported, not applicable, redacted, expired, and incomplete. Detailed provider usage must specify whether reasoning/cache counters are subsets or disjoint categories. Aggregation rejects incompatible definitions.

### Comparison experiment

Experiment ID, task/context references and digests, candidates, objective assessments, evaluation plan, authorization revision, execution path, limits, isolation declaration, assignment method/probabilities when applicable, and host acceptance for immediate execution. Independent runs and incomplete candidates remain explicit. Distinguish proposed, accepted, queued, running, completed, incomplete, canceled, and blocked experiment states; freeze their transition table before stage 3.

## 6. Transport, idempotency, and deadlines

Proposed commands: `jevdrill route`, `jevdrill report`, `jevdrill inspect`, `jevdrill maintenance`, and `jevdrill notifications`. Standard input/output JSON applies to machine operations; human summaries are explicit modes. Proposed exit codes: 0 for a valid handled response (including non-ready), 2 for invalid input/version, 3 for idempotency conflict, 4 for infrastructure failure preventing a normal response. The JSON status remains authoritative; do not infer ready from exit code zero.

The host starts the total deadline before spawning the CLI so startup counts. Pass remaining duration to application processing, reserve bounded time for validation/fallback/commit, and use monotonic timers locally. Do not compare monotonic clocks across processes. A caller timeout may race a committed result: retry the same key to retrieve the stored result, never launch from a missing or partial response.

Propose canonical payload hashing via a documented cross-language JSON canonicalization convention, with decimal strings for costs. The digest includes every behavior-changing field; credentials and transport-only tracing are excluded. The uniqueness key is `(scope, operation, idempotency_key)`. Store payload digest and final response atomically with the decision. Event deduplication also uses event identity and detects conflicting reuse.

Bound both input and output bytes before decoding. Never use a shell to interpolate request content. Report delivery uses a host-owned queue, redacted before persistence, with retries and durable acknowledgment. File queue/SQLite implementation and crash recovery must be proved in the adapter tests. Routine record replay is not permission to recreate explicitly deleted data.

## 7. Storage and identity proposal

Use OS-standard per-user config/data/cache directories with explicit overrides, not paths copied from a development host. Project files stay in `.jevdrill/`; the database and private evidence stay outside the repository. Persist workspace identity locally and bind it to declared project identity and execution target. Moving a workspace must not change project ID or accidentally merge independent execution histories.

Proposed SQLite table families:

- `projects`, `workspaces`, `settings_revisions`, `inventory_snapshots`.
- `resources`, `resource_revisions`, `source_occurrences`, `admission_decisions`, taxonomy relationships.
- `tasks`, `routing_contexts`, `routing_decisions`, `execution_plans`, `decision_candidates`, `jev_judgments`.
- `execution_runs`, `execution_events`, `metric_definitions`, `measurements`, `evaluations`, `objective_assessments`.
- `routing_policies`, `evidence_revisions`, `evidence_contributions`, `policy_evaluations`.
- `comparison_experiments`, candidate/run links, `idempotency_records`, `notifications`, `maintenance_jobs`, `deletion_records`, `artifacts`.

Use foreign keys, unique immutable revision identities, transactional event ingestion, and explicit source-to-derived contribution links. Propose WAL with bounded busy handling on a local disk; measure contention and recovery rather than assuming WAL supplies interactive priority. Background jobs limit write batches and yield. Migrations must support backup/recovery and fail without partially applying incompatible changes.

Content-addressed artifacts need an index carrying scope, retention, reference ownership, and encryption metadata. Do not deduplicate private content across projects in a way that bypasses deletion or exposes shared existence. Public immutable resource bundles may be deduplicated separately. Exact tables/DDL and artifact layout are implementation freeze outputs, not already emitted schemas.

Explicit deletion removes contributions, cached decisions dependent on deleted context, and active/archive payloads. Keep minimal tombstones; apply them to delayed reports and restored backups before permitting analysis. Recompute affected projections and mark policy validation stale. Ordinary content expiration retains redacted measurements. Define recovery for a crash between file and database operations using tracked pending operations rather than claiming filesystem/SQLite writes are jointly atomic.

## 8. Vocabulary enforcement proposal

`docs/vocabulary.yaml` is authored machine authority. Generated glossary and future HTML displays cite its hash. Accepted concepts are marked accepted; proposed implementation additions remain proposed until contract freeze. The source registry must identify these machine definitions separately from human intent documents.

Deterministic checks should cover unique concept IDs, valid module owners, code-name casing, known public type/field aliases, module paths/import graph, required concept references, generated glossary freshness, and generated JSON Schema freshness. Parse Python AST and YAML/JSON structure; do not grep every occurrence of “state” or “plan” and pretend to understand its meaning. Prose checks apply narrowly scoped exact aliases and allow reasoned exceptions. Imported evidence, historical decisions, generated provider types, and quoted external identifiers have explicit source roles.

Negative fixtures: duplicate concept ID; unknown owner; forbidden public alias; illegal import; stale generated glossary; undocumented exception; ambiguous alias collision. Positive fixtures: external JEV `state`, imported `LaunchSpec`, ordinary local variables, and unchanged research artifacts. A negative fixture passing must fail the check suite. Vocabulary validation does not claim proof that two differently worded requirements are semantically identical.

## 9. Evaluation and implementation gates

Proposed first delivery sequence:

1. BAML compatibility proof; vocabulary registry schema and checks; BAML-authored contracts, generated Pydantic/JSON Schema and fixtures; reviewed import graph.
2. Storage migrations/idempotency and catalog importer preserving unvalidated research status.
3. Inventory bridge, costing and bounded JEV selection with deterministic fallback/replay.
4. Agent-harness before-launch and after-completion bridge, durable reporting, dry-run exclusions, Windows/macOS/Linux conformance.
5. Held-out implementation/review/documentation evaluation and readiness review.

Check malformed schemas, conflicting IDs, unsupported effort, unknown cost under a cap, deadline exhaustion, false readiness, duplicate guidance, output truncation, report reordering, crash/retry, deleted-task replay, missing BAML client, privacy-restricted JEV calls, and stale inventory. Reuse the existing 55 research tests without treating them as product acceptance.

For quality non-regression, propose task-family paired comparisons with a one-sided uncertainty bound on acceptance loss and a predeclared practical margin. Do not pick a numeric margin merely to pass results. Define sample size and acceptable margin in the evaluation plan using pilot variance and task consequence before exposing the holdout. No observed failures is not proof of zero failure probability. Cost comparisons include routing overhead; model selection still uses the accepted one-attempt estimate until stronger evidence supports retries.

## 10. Remaining proof obligations

The planned product interview is complete. These are technical verification/drafting tasks, not assumed capabilities:

- Verification of the selected `baml-language-0.20.1` pin, matching Python runtime dependencies, Python/CLI interoperability, safe usage events, timeout enforcement and package inclusion.
- Complete public BAML definitions, generated language types/schemas, strict boundary validators, exact event transitions, and SQLite DDL.
- Agent-harness adapter implementation across launch paths, schema-version negotiation, and confirmed usage extraction.
- Cross-platform process control, credential backend, scheduler integration, archive format and recovery tests.
- Vocabulary linter implementation and CI wiring; this document does not claim they exist.
- Measured JEV latency/token budget and operational defaults compatible with the five-second target.
- Initial enabled resources with rights/dependency review, actual task fixtures, and calibrated release margins.
- Explicit Git repository provenance and governed-pipeline dry-run adoption, including HTML/Markdown roadmap consistency and YAML authority registration.

Do not mark these complete based on this proposal alone. Canonical adoption remains deferred until source coverage and the chosen pipeline compatibility path are checked.
