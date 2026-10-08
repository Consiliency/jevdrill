# JEV Drill: accepted design input

Status: human-authored intake; not adopted canonical documentation.
Source: the design interview in this chat, following review of the product draft.
Authority: this records explicit user selections and corrections. Proposed implementation details remain identified as proposals. No pipeline adoption, source archival, or mirror refresh has been performed.

## How to use this bundle

Read this file together with [the original product draft](../docs/jevdrill-spec.md) and [the current-state and gap assessment](jevdrill-current-state.md). The draft remains a preserved design input. Where this interview explicitly changed it, the decisions below define the accepted target. Unchanged draft requirements remain input requirements; synthesis must check them rather than silently dropping them.

Decision IDs `JD-001` through `JD-082` are stable references assigned during consolidation and subsequent refinement. They are not governed-pipeline task IDs or agent-harness exit-criterion IDs. Each entry has a target document family for later adoption. These mappings account for accepted choices; final canonical documents and exact anchors are not yet created.

Accepted decisions define intended behavior, not evidence that the behavior already exists. When current code differs, record a gap. When two requirements conflict without an explicit correction, keep an open question and block only affected work. Do not let synthesis invent an accepted answer.

## Vocabulary and implementation structure

### JD-001 — Enforced vocabulary

Target: implementation RFC and vocabulary contract.

Enforce canonical vocabulary across application code and documentation. Each concept has one English term, definition, code identifier, relevant ownership, and scoped discouraged aliases. Imported research, quotations, and external API names have explicit exceptions. Automated checks enforce known names and structure; they do not claim to prove semantic correctness of arbitrary prose.

### JD-002 — Core concepts

Target: implementation RFC and vocabulary contract.

| English term | Identifier | Meaning |
|---|---|---|
| Settings | `settings` | Persistent user, project, or machine preferences |
| Execution plan | `execution_plan` | Proposed model, access route, effort, guidance, and tool requirements |
| Routing decision | `routing_decision` | Selection of an execution plan or an explicit non-ready result |
| Execution run | `execution_run` | One actual attempt to carry out a plan |
| Routing evidence | `routing_evidence` | Observations and derived estimates relevant to selection |
| Routing policy | `routing_policy` | Versioned rules selecting plans |
| Routing context | `routing_context` | Information assembled for a particular routing request |
| Comparison experiment | `comparison_experiment` | Deliberate comparison of execution plans; “bakeoff” and “benchmark showdown” are user-facing labels |
| Observed execution | `observed_execution` | Ordinary harness work used as observational evidence |
| Controlled experiment | `controlled_experiment` | Deliberate execution under defined comparison conditions |
| Optimization objective | `optimization_objective` | Acceptance requirements, optimized metric, constraints, and cost basis defining a comparison |
| Capability mismatch | `capability_mismatch` | Disagreement between declared and runtime harness capabilities |

Restrict ambiguous use of bare “configuration” and “state” in owned interfaces. Preserve external API terminology through explicit exceptions. Some entries describe event or evidence concepts, not necessarily new Python classes; class design remains part of schema work.

### JD-003 — First integration and repository ownership

Target: architecture and roadmap.

Build a standalone Python package in this repository, under `src/jevdrill/`. Put a small adapter in agent-harness and provide a local debugging CLI sharing the same contracts. Existing research scripts remain separate; inspect for reuse instead of importing them wholesale into the product.

### JD-004 — Modules and dependency boundaries

Target: architecture and implementation RFC.

| Module | Responsibility |
|---|---|
| `contracts` | Shared request, decision, plan, run, and reporting types |
| `settings` | Preference loading and override resolution |
| `catalog` | Resources, revisions, taxonomy, admission |
| `inventory` | Models, access routes, tools, availability |
| `context` | Relevant task and project facts |
| `routing` | Feasibility, comparison, and selection |
| `guidance` | Assembly and checking of selected instruction content |
| `storage` | SQLite, migrations, artifacts |
| `telemetry` | Decision events, execution reports, outcomes |
| `evaluation` | Acceptance checks, rubrics, and objective-specific assessments |
| `analysis` | Comparable task groups, accumulated evidence, and policy proposals |
| `experiments` | Comparison proposals, scheduling, execution, and host coordination |
| `integrations` | External clients, including JEV |
| `application` | Coordination across components |
| `costing` | Raw token cost and separate subscription adjustment |
| `cli` | Local commands |
| `objectives` | Later: recommend optimization objectives within configured authority |

Start responsibilities as modules and split them into packages when justified. Mirror responsibility names in tests. No catch-all `utils`, `helpers`, or `common` modules. Automatically enforce dependency rules: `contracts` does not import application modules; `routing` does not directly query databases or call external services; `application` coordinates effects; circular imports fail checks. JD-064 settles evaluation/analysis/experiment ownership. The exact allowed-import graph remains open.

### JD-005 — Naming, types, and checks

Target: implementation RFC and vocabulary contract.

Use `snake_case` for modules/functions/fields, `PascalCase` for classes, and explicit identifiers such as `routing_decision_id`. Ordinary local names such as `index` need no glossary entry. Enforce formatting, lint, types, dependency boundaries, and generated-schema consistency. Exceptions are narrow and justified.

Strict type checking covers the application package; tests and research use a lighter standard. Pydantic validates external and stored data. Internal functions trust validated objects and use explicit types. Wrap untyped external clients in `integrations`; avoid generic dictionaries between modules when a named contract applies.

### JD-006 — Vocabulary authority and renames

Target: vocabulary contract and governance registry.

`docs/vocabulary.yaml` will be the machine authority, with a generated `docs/vocabulary.md`. Register that authority during adoption; canonical prose references it rather than maintaining a second dictionary. Registry entries include definitions, code forms, module ownership, scoped forbidden aliases, and exceptions.

Rename internal code and docs atomically. Preserve published interfaces through version-specific compatibility handling, migration tests, and deprecated-name records. Do not keep unrestricted aliases throughout the application. A seed registry and glossary renderer now exist; full code/prose vocabulary linting remains implementation work.

### JD-007 — Runtime and distribution

Target: implementation RFC and release readiness.

Support Linux, macOS, and Windows in the first release. Distribute a versioned Python package installed in an isolated environment, exposing `jevdrill`. Choose and test explicit Python versions. Use a synchronous core with bounded experiment workers, timeouts, and short transactions. Scheduling, process behavior, paths, and isolation must be tested on each OS; container capability is a separate prerequisite for internal code experiments.

## Contracts, execution identity, and durability

### JD-008 — Schema authority

Target: implementation RFC.

Original choice: Pydantic definitions generate checked-in, versioned JSON Schema. JD-082 supersedes the authored-source choice with BAML where generation capability is proved. Automated checks still reject stale generated schemas. Explicit validators and tests still cover invariants not expressible by the generated schema.

### JD-009 — Strict boundaries

Target: implementation RFC.

Reject unknown fields and unsupported contract versions at external boundaries. Allow explicitly namespaced optional metadata in `extensions`; extensions do not alter execution behavior. Breaking changes require a new major version. Exact compatibility matrix and migration rules remain to be specified.

### JD-010 — Routing statuses

Target: implementation RFC.

| Status | Meaning |
|---|---|
| `ready` | A verified compatible plan is selected |
| `needs_context` | Missing facts prevent selection |
| `constraint_conflict` | Binding requirements contradict each other |
| `no_compatible_plan` | Requirements are understood but no available plan satisfies them |
| `routing_failed` | Technical failure prevents a trustworthy decision |

Each status has a distinct validated shape. `ready` requires a selected plan; non-ready results cannot contain a selected executable plan, although alternatives/setup proposals may be described. A verified fallback can produce `ready` with its use recorded.

### JD-011 — Immutable plans

Target: implementation RFC.

Selected execution plans are immutable and have stable IDs. Changing model, effort, access route, or guidance creates a linked replacement. Runs distinguish selected and applied plans and record substitutions. Retrying the same plan creates another run. Availability checks are separately recorded because availability changes.

### JD-012 — Idempotency

Target: implementation RFC.

Record-creating operations carry explicit idempotency keys. The same key and payload returns the existing result; different payload with the same key produces a conflict. Intentional retries receive new run IDs linked to earlier runs. JEV Drill deduplicates its records; the harness deduplicates its execution. Recording a routing decision does not launch work.

### JD-013 — Reporting and delivery queue

Target: implementation RFC and runbook.

Use a shared versioned execution-report/event contract supporting partial, delayed, retried, and corrected reports. The adapter reports automatically through hooks or explicit tool/CLI calls using the same meanings. Preserve corrections as new events. Record actual settings when observable and unknowns otherwise.

The adapter owns a persistent transport queue: save before delivery, retry with the same key, acknowledge only durable storage, then remove. Bound size and retention and expose failure. Privacy rules apply to queued copies. JEV Drill owns analytical collection, validation, analysis, and long-term records; this host queue is a transport responsibility.

### JD-014 — CLI transport

Target: implementation RFC.

Agent-harness invokes the CLI with versioned JSON on standard input/output, one request/response per invocation. Standard output contains only the response; diagnostics go to standard error. Separate routing and reporting commands. Define exit codes, deadlines, and cancellation. The CLI and maintenance commands share application functions. Measure startup overhead before introducing a persistent service.

### JD-015 — Durable decisions and contention

Target: implementation RFC.

Return `ready` only after the decision is durably stored. Use bounded contention waits and short writes; perform analysis and experiments outside transactions. Background work yields/retries to favor interactive routing. Exhausted storage deadlines produce typed failure, not an unrecorded ready result. The exact priority mechanism remains implementation work.

## Routing and cost

### JD-016 — Default objective

Target: PRD and routing RFC.

Choose the lowest expected token cost among plans expected to meet task-specific quality requirements and acceptable completion time, after hard constraints. Users/projects can override the objective. Do not default to maximum quality regardless of cost. Capability readiness establishes executability, not successful task outcomes.

### JD-017 — Acceptance requirements

Target: PRD and test plan.

Use explicit user requirements first, then versioned task-family defaults. Label inferred criteria. Ask about ambiguity when it materially changes selection. Use understandable criteria and evidence categories, not an invented universal quality score.

### JD-018 — Bounded trials and escalation

Target: routing RFC.

Cheaper plans can be tried for low-consequence tasks with meaningful checks. More consequential or poorly checkable tasks need stronger supporting evidence. Failed acceptance may trigger a new routing decision using the failure and remaining budget. A replacement must address the failure; expense alone is not justification. The harness owns execution authorization; bound attempts, total spending, and time. Separate infrastructure failure from task-quality failure.

### JD-019 — Selection boundaries and evidence precedence

Target: routing RFC.

Code filters hard constraints and narrows candidates using explicit task tags, project settings, and catalog relationships. JEV judges fit/sufficiency within bounded candidates and calls. Code applies the objective and validates the result. Relevant measured evidence takes precedence over unsupported JEV judgments. Sparse/stale/mismatched evidence affects confidence without automatically proving ineligibility.

### JD-020 — Guidance admission

Target: catalog RFC.

Allow exact revisions through distinct paths: policy admission (provenance, reuse rights, conflicts, dependencies) or explicit user enablement for a scope. Neither implies measured benefit. Everything else is inspectable/experiment-only when authorized, not silently injected. Changed content requires an applicable new admission or enablement decision.

### JD-021 — Governing instructions and composition

Target: guidance RFC.

The harness supplies instruction authority and active guidance. JEV Drill may inspect referenced files but cannot independently elevate their authority. Exclude conflicting optional guidance, avoid duplicate injection, count required guidance against context budgets, and expose unresolved conflicts.

At most two optional guidance resources per plan, each with a distinct role and explicit order. Required instructions are outside that count but inside context limits. Always consider no optional guidance. Do not silently rewrite or truncate instructions to fit.

### JD-022 — Deterministic fallback

Target: routing RFC.

When JEV fails or returns invalid data, use a verified compatible configured default if available. Respect governing guidance; optional additions require explicit fallback rules. Disclose fallback/evidence limitations. Otherwise return `routing_failed`. Failure cannot expand spending, provider, or privacy permissions.

### JD-023 — Cost authority and adjustments

Target: costing RFC.

Separate cost calculation from selection. Always expose `raw_token_cost` using undiscounted token rates. Optionally expose `adjusted_token_cost` using subscription information, discount rules, assumptions, and freshness. Keep actual charges as `observed_cost`. Default `routing_cost_basis` to raw cost; users may enable adjustment or let the caller handle it. Subscription discount does not silently affect default ranking.

Use token-based monetary estimates rather than assigning an implicit monetary value to local hardware. Quotas, hardware limits, and timing remain separate constraints. Per-access-route discount settings are allowed; exact adjustment formulas remain open.

### JD-024 — Estimate scope and unknowns

Target: costing RFC.

Initially estimate one execution attempt: input context, guidance, expected output, and applicable token categories. Report routing overhead separately. Do not predict retry-adjusted costs without evidence. Unknown cost is not zero and cannot establish a hard spending limit. Such a plan remains visible but selection needs an explicit preference/fallback rule rather than a claim it is cheapest.

### JD-025 — Inventory and freshness

Target: inventory RFC.

Maintain a versioned registry with provider refresh adapters and explicit local overrides. Record source and verification time, and bind native effort to the actual access route. Maintenance refreshes; routing uses a recorded snapshot.

Separate price freshness from capability readiness. A configured grace period may permit disclosed stale estimates, but those estimates cannot prove hard-spending compliance. Required stale capabilities must refresh before `ready`; otherwise use a verified alternative or return non-ready.

### JD-026 — Ties and explanations

Target: routing RFC.

For meaningfully tied feasible candidates, prefer the user's default then a stable order. Randomization belongs to separately authorized exploration. Record ties and insufficient evidence as comparison opportunities.

Return a concise human summary and a full structured record: selected plan, objective/cost basis, cost/time estimates and uncertainty, acceptance rationale, exclusions, alternatives, proposals, and referenced versions. Unknown estimates stay unknown.

### JD-027 — Caching and replay

Target: routing RFC.

Reuse only when relevant inputs match and readiness remains fresh. Include task requirements, authority, guidance, objective, settings, policy/evidence/catalog versions, and applicable inventory and authorization information. Similarity permits learning, not automatic decision reuse. A response records the reused decision.

Preserve inputs, candidates, JEV judgments, and revisions for deterministic replay of filtering, costing, tie-breaking, and selection. Calling JEV again is a new evaluation. Deletion can make exact replay unavailable; mark this explicitly.

## Learning, experiments, and harness cooperation

### JD-028 — Experiment ownership

Target: architecture and experiments RFC.

JEV Drill owns experiment proposals, collection, analysis, evidence updates, and policy proposals. It supports internal execution and harness-assisted execution. The harness may execute competing plans and select a result; it does not become the analytical authority. Routine observed executions are expected to supply most evidence.

### JD-029 — Analysis triggers

Target: analysis RFC.

Analyze a minimum batch of new comparable outcomes with periodic checks; skip unchanged evidence. Routing volume may trigger investigation of gaps but is not quality evidence. Thresholds are explicit settings. Schedule work only when resources and authorization permit.

### JD-030 — Comparable groups

Target: analysis RFC.

Use explicit versioned grouping rules for task type, acceptance criteria, relevant framework/language, environment, difficulty, context size, and constraints. Model/effort/guidance are comparison variables, not automatic reasons to separate tasks. Broad groupings support weaker claims. Keep observational associations separate from controlled effects.

### JD-031 — Evidence and policy updates

Target: analysis RFC.

Record outcomes immediately; update scoped evidence and derived estimates under the existing policy. Such updates can change selection without changing rules. Rule changes create a new policy version and require promotion. Record evidence revisions in each decision. One outcome does not establish global superiority; scopes and uncertainty survive aggregation.

### JD-032 — Experiment authorization

Target: experiments RFC.

Support standing authorization with project/task scope, spend per experiment/day, delay, concurrency, provider, data-handling, and background-work limits. Missing necessary limits do not authorize automatic experiments. Default to observation during ordinary work; deliberate recommendation variation needs separate standing authorization and stays within task constraints.

Local retention/analysis is enabled by default under JD-043. That correction does not erase separate permissions for external provider use, deliberate exploration, or policy promotion. The exact initial local experiment enablement and budget defaults still need explicit settings.

### JD-033 — Execution paths and isolation

Target: experiments RFC.

Internal experiments support text and code tasks. Internal code execution requires restricted containers: copied inputs, no credentials/host sockets, no network by default, bounded CPU/memory/time, and no consequential external effects. If the runtime is unavailable, code experiments are unavailable; routing and text experiments can continue.

Observed executions use the host's isolation, recorded as evidence. A harness-assisted comparison requires declared isolation adequate for its task, but does not inherit an unconditional requirement to use JEV Drill's internal container runner.

### JD-034 — Immediate and deferred comparisons

Target: experiments RFC.

Offer immediate bakeoffs when authorization, replay/context access, resources, and task limits permit. A host can accept a comparison that delays the task within standing authority, run candidates, and use its preferred result. Otherwise execute the ordinary selected plan and queue eligible comparison work. Background analysis need not coincide with the original task.

### JD-035 — Priority and partial completion

Target: experiments RFC.

Prioritize recurring uncertainty and meaningful potential quality/cost benefits, accounting for experiment cost and available resources. Deduplicate equivalent proposals and use explicit versioned prioritization rules.

If a candidate fails or times out, use a completed acceptable result and preserve incomplete comparison status. Remaining runs may be canceled; continued research requires remaining budget/authority. Timeout provides latency evidence, not an unobserved quality verdict.

### JD-036 — Host capabilities

Target: integration RFC.

Declare capabilities in `.jevdrill/harnesses.yaml` keyed by `harness_id`, with machine overrides in ignored `.jevdrill/local.yaml`. Requests supply current limits. Record concurrency, isolation, telemetry, evaluation, and cancellation abilities. Only use capabilities confirmed by both declaration and runtime; runtime cannot expand configured permissions.

Return a `capability_mismatch` diagnostic identifying declared/runtime/effective values, affected operations, and evidence-supported resolution recommendations. Block only dependent operations. Do not silently rewrite declarations or grant permissions.

### JD-037 — Host choice and measurement provenance

Target: telemetry and experiments RFC.

Hooks and explicit calls deliver one event contract. JEV Drill collects measurements deterministically wherever directly observable; host/provider measurements retain source and method. Missing values are unknown.

Store host selection and reasons separately from evaluation results. A preference cannot turn a failed check into a pass. Newly supplied requirements can inform future comparisons; preserve original evaluation criteria.

### JD-038 — Evidence thresholds

Target: analysis RFC and test plan.

Use versioned task-family evidence requirements: comparable sample counts, acceptance results, uncertainty, recency, exact revisions, observational versus controlled origin, and missing/failed/canceled runs. Thresholds are explicit provisional settings to calibrate against baseline data, not invented probabilities.

### JD-039 — Objectives and reassessment

Target: objectives RFC; automatic objective recommendation is deferred.

Assess one experiment against multiple objectives. Keep measurements primary and winner classifications derived. Preserve assessment history when objectives change. Future `objectives` logic may recommend objectives using deadlines, cost constraints, subscriptions, and preferences, but applying them requires explicit settings or caller acceptance. Raw cost remains available under any objective.

### JD-040 — Policy promotion

Target: analysis RFC and release readiness.

Automatically propose/test policies. Promotion needs separate standing authority; experiment participation alone is insufficient. Run offline checks, then a limited authorized rollout with predefined regression limits and rollback. Replay alone cannot supply counterfactual outcomes for unexecuted plans. Use controlled experiments where needed; retain previous policies and scope changes.

Owner clarification on 2026-09-30: the first promoted policy may change only the ordering of already-eligible candidates within an approved task group. Caller constraints, permissions, spending limits and required guidance retain precedence. Pin the evaluated model and guidance revisions; retain the previous policy and restore it only while its evidence and promotion authority remain current. Implementation approval does not activate a policy.

## Telemetry, metrics, retention, and maintenance

### JD-041 — Metric definitions and baseline coverage

Target: telemetry RFC and metric contract.

Version metric definitions with stable identity, meaning, units, measurement method, applicable optimization direction, missing-value reasons, and compatibility rules. Meaning changes cannot silently merge with earlier observations.

The accepted baseline covers acceptance checks; routing/execution/evaluation durations; first-answer timing; waits when observable; input/cache/output/reasoning token usage; raw/adjusted/observed costs; completion/error/retry/cancel/timeout events; human corrections and choices; guidance identity/order/size; and actual model/effort/harness/tool/isolation/environment metadata. Hosts may omit unavailable measurements explicitly rather than fabricate zeros. Exact field spellings beyond already agreed identifiers remain schema work.

Preserve provider counting semantics so reasoning/cache subsets are not double counted. Sum costs across candidates, but measure parallel elapsed time rather than summing overlapping durations. Distinguish estimates, direct observations, provider reports, host reports, and evaluator judgments.

### JD-042 — Win assessment and aggregate analysis

Target: analysis RFC and test plan.

Use practical-difference thresholds and uncertainty. A single-task advantage is scoped to that task; future preference needs comparable evidence. Keep practical equivalence, insufficient evidence, and non-comparability separate.

Assess cost, speed, task quality within budgets, token efficiency at adequate quality, reliability, intervention, and guidance benefit as separate objectives. Retain alternatives not dominated on all relevant dimensions. Aggregate acceptance, sample counts, uncertainty, median/tail latency, deadline rate, cost per accepted task, retries, infrastructure failures, and interventions. Include failed-attempt costs in cost per accepted task; zero accepted tasks makes that ratio undefined. Later calibration and prediction-error analysis use preserved estimates and outcomes.

### JD-043 — Local defaults and external processing

Target: PRD and privacy/retention ADR.

Local task/context retention and local analysis are enabled by default with opt-out, credential exclusions, and project exclusions. External providers for background experiments require separate authorization; ordinary execution provider permission does not automatically extend to experiments. Compact retained measurements must remain redacted and avoid sensitive content hidden in labels or reasons.

### JD-044 — Retention and archives

Target: retention RFC and runbook.

Keep replayable task content active for 30 days, then offer local cold storage. After seven days without an answer, automatically archive locally. Cold archives expire one year after archival, with advance notice and configurable retention. Verify archives before removing active copies. Keep them outside routine analysis/experiments until explicitly restored. Task deletion covers active and archived copies.

Keep compact redacted measurements until explicitly deleted. Mark when content expiration prevents replay or evaluation under a new rubric. Thirty days is the active-storage period, not a guarantee that all data is deleted on day 30. JD-066 settles notice channels; JD-070 establishes encrypted archives and OS-managed keys. Cryptographic format and recovery implementation remain open.

### JD-045 — Maintenance

Target: runbook and implementation RFC.

Use an OS-scheduled local maintenance command that processes eligible work and exits. Configure scheduling explicitly; prevent overlaps and persist resumable progress. Maintenance owns eligible refresh, analysis, archival, and experiment scheduling through the application layer. Exact scheduling adapters and resource detection remain open.

## Evaluation and delivery

### JD-046 — Delivery stages

Target: roadmap.

1. Routing: contracts, vocabulary checks, catalog, inventory, costing, CLI, harness reporting.
2. Local learning: outcome analysis, evidence updates, maintenance, retention, archival.
3. Controlled experiments: internal isolated execution, immediate harness-assisted bakeoffs, policy evaluation, authorized promotion.

Specify shared contracts up front and deliver working acceptance-tested stages. JD-065 assigns immediate harness-assisted execution to stage 3; its contract belongs in the initial design. Do not postpone all quality evaluation until stage 3: every stage needs its own acceptance checks.

### JD-047 — Supported initial task families

Target: PRD and test plan.

Initially validate code implementation, code review, and technical documentation. Preserve other catalog domains; use verified defaults with disclosed evidence gaps outside measured scope. Do not claim cross-domain validation from these initial evaluations.

### JD-048 — Independent evaluation

Target: test plan.

Use independent fixtures and task-specific rubrics. Implementation checks include task tests and regressions; review checks include known defects, false positives, severity, and actionable findings; documentation checks include factual accuracy, coverage, references, and examples. Candidate-written tests supplement independent checks. Separate objective checks, user feedback, and model judgments; conflicting results remain visible and missing evidence is unknown.

### JD-049 — Data splits

Target: test plan.

Separate development, validation, and holdout sets. Keep related repository/template tasks together where practical. Record exposure; repeated tuning against a holdout requires retirement or replacement. Independent evaluator and dataset versions are preserved.

### JD-050 — Baselines

Target: test plan.

Compare against the user's fixed default, a simple deterministic cheapest-feasible selector, the selected model without optional guidance, and the previous policy, where applicable. Distinguish resource feasibility from demonstrated quality. Include routing overhead when claiming total savings and preserve paired conditions.

### JD-051 — Release and promotion gates

Target: release readiness.

Mandatory contract, permission, privacy, and idempotency checks must pass. Set quality minima, allowed regression margins, cost/time objectives, and evidence requirements before held-out evaluation. Insufficient evidence leaves gains unproven. Revised thresholds require recorded changes and fresh evaluation. Tests establish coverage-limited evidence rather than universal guarantees.

## Canonicalization and source governance

### JD-052 — Fleet-compatible bundle

Target: governance registry.

Prepare a governed-pipeline-compatible source bundle now and adopt after refinement. Keep YAML/code authorities explicit. Verify or implement a deterministic agent-harness Markdown roadmap representation preserving exact phase aliases, `EC-*` criteria, `IF-*` gates, and dependencies. Do not independently maintain contradictory roadmap facts.

### JD-053 — Brownfield classification

Target: governance registry.

Use brownfield adoption because research code/tests/data/docs already exist. Classify accepted English intent, supporting evidence, reusable implementation, and superseded history separately. Adoption is not permission to treat unvalidated research as product functionality.

### JD-054 — Intent versus current behavior

Target: governance registry and architecture.

Accepted requirements define the target; inspected code establishes current behavior. Gaps, reuse decisions, and unresolved conflicts remain explicit. Do not rewrite intent to fit existing code or describe plans as implemented.

### JD-055 — Supersession and coverage

Target: decision records and governance registry.

Latest explicit user corrections supersede earlier choices, with history and rationale. Every accepted decision maps to an active specification section or explicit deferral. Preserve unresolved conflicts instead of guessing. This ledger's target-family mappings are the initial coverage map; exact canonical anchors follow adoption.

### JD-056 — Open questions

Target: governance registry and roadmap.

An unresolved question has an owner, affected requirements, and affected stage. It blocks only dependent work. A synthesizer may recommend an answer but cannot label it accepted.

### JD-057 — Consolidation checkpoint

Target: source bundle and current-state assessment.

Consolidate now, inspect existing code, record supersession, map decisions, and continue the interview from the remaining blockers. Do not run canonical adoption yet. This document and its companion fulfill that checkpoint, not the completed implementation specification.

## Superseded proposals and clarifications

### JD-058 — Objective history

Target: objectives ADR.

The assistant initially recommended quality-first ranking. The user rejected the tendency to favor expensive models. JD-016 replaces it with adequate quality and time first, then minimum token cost.

Early discussion treated subscription discounts as routing adjustments, then excluded them, then explicitly separated them into `costing` with user choice. JD-023 is the final decision: raw cost always available and default; adjusted cost optional. No earlier exchange authorizes silently ranking by a discount.

### JD-059 — Experiment ownership history

Target: experiments ADR.

The assistant suggested agent-harness own experiment execution/coordination. The user required experiments, analytical collection, and analysis inside JEV Drill. Later the user explicitly added immediate harness-assisted execution and host result selection. JD-028 through JD-037 reconcile these: JEV Drill owns the experiment; the host can execute and report; an internal runner remains supported.

Background comparisons were initially the default with waiting only on direct request. The later immediate-bakeoff decision permits host acceptance under standing authority and task limits (JD-034). Internal container requirements apply to intentional internal code experiments; observed harness work uses host isolation (JD-033).

### JD-060 — Retention history

Target: retention ADR.

Initial opt-in for replayable local content was explicitly replaced by default local retention/analysis (JD-043). An initial 180-day summary proposal was replaced by indefinite redacted measurements until deletion (JD-044). A proposed seven-day unanswered-prompt deletion was rejected in favor of automatic local archival. Archive expiration is one year after archival. External experiment provider authorization remains separate.

### JD-061 — Document structure history

Target: governance ADR.

The assistant's initial Markdown-only document layout was not accepted. Repository inspection led to fleet-compatible intake followed by HTML-first governed adoption, preserving explicit machine authorities and verifying the harness roadmap bridge (JD-052). Do not make a new handwritten Markdown implementation spec an independent canonical authority by accident.

### JD-062 — Delivery scope history

Target: roadmap ADR.

The original draft deferred the internal experiment runner and policy learning. The interview accepted specifying these components and delivering three stages (JD-046). Stage-1 routing is usable before the full learning/experiment product exists. Exact version/release names remain open.

### JD-063 — Multi-objective evidence history

Target: analysis ADR.

The user clarified that experiments may classify wins under several objectives at once and that preserving data for later reassessment is primary. JD-039 through JD-042 replace any interpretation that a single permanent winner is the experiment's complete result. Retention still limits evaluations requiring deleted content.

### JD-064 — Evaluation, analysis, and experiment modules

Target: architecture and implementation RFC.

Add separate `evaluation`, `analysis`, and `experiments` modules with the responsibilities in JD-004. `telemetry` continues to collect reports; `application` coordinates components. This resolves Q-02's ownership question without freezing the complete import graph or internal interfaces.

### JD-065 — Bakeoff delivery timing

Target: roadmap and experiments RFC.

Enable immediate harness-assisted bakeoffs in stage 3 alongside internal controlled experiments. Stage 1 defines the comparison/reporting contracts and collects ordinary execution outcomes; stage 2 analyzes that evidence. This sequences delivery without removing the accepted immediate-bakeoff requirement. Isolation details, limits, and cancellation interfaces remain implementation questions.

### JD-066 — Persistent local notifications

Target: maintenance RFC and runbook.

Maintain a persistent local notification inbox for archive prompts, failures, and required decisions. Expose it through the CLI and surface notices when the harness next connects. Optional desktop notifications provide additional alerts; the inbox remains authoritative if an alert is missed. Each applicable notice records its deadline and automatic action, including archival after seven unanswered days. External notification delivery is not included in this decision.

### JD-067 — Project and workspace identity

Target: settings and context RFC.

Declare a stable `project_id` in `.jevdrill/project.yaml` and track workspace identities separately. Directory moves preserve project identity. Git worktrees share project settings and scoped evidence while retaining separate execution contexts. A copied or forked project can explicitly receive a new project identity. Discovery stops at the declared project boundary. This also supports non-Git projects; neither a remote URL nor an absolute filesystem path is the sole project identity. Exact workspace identity allocation and local override resolution remain implementation work.


### JD-068 — Cross-project evidence sharing

Target: analysis RFC and privacy ADR.

Learn within project scope by default. Users may opt into sharing redacted performance measurements across their local projects. Shared evidence retains originating task conditions and provenance; it does not transfer project-specific instructions or permissions, or silently impose one project's preferences and acceptance criteria on another. Public benchmark evidence may remain available across projects. This is local user-wide sharing, not permission to upload evidence or share it between users.


### JD-069 — Deletion of derived evidence

Target: storage and analysis RFCs, privacy ADR.

Explicit task deletion removes its measurements and evidence contributions, including local cross-project shared copies, and recomputes affected estimates. Preserve only a minimal deletion record sufficient to prevent delayed telemetry from recreating the task. Mark supporting evaluations of affected promoted policies stale and revalidate them; evidence removal alone does not establish that a policy is incorrect and does not automatically require rollback. This explicit-deletion behavior is distinct from scheduled task-content expiration, which retains redacted measurements under JD-044. Exact deletion-record fields, propagation, and recovery behavior remain implementation work.

### JD-070 — Encrypted cold archives

Target: storage RFC, privacy ADR, and recovery runbook.

Encrypt cold archives by default and store their keys in the operating system's credential store. Automatic archival must work without an interactive password prompt on every run. Portable export requires a separate recovery-key or passphrase flow. If a key is unavailable, report the failure through the local inbox and retain pending content; never silently create an unencrypted archive. This is a visible exception to normal archival timing, not successful archival. Archive format, key recovery/rotation, supported OS credential backends, and handling of prolonged key unavailability remain implementation questions. This decision does not claim that the active SQLite database or all active task artifacts are encrypted by the application.

### JD-071 — Task-scoped collection and exclusions

Target: context and telemetry RFCs, privacy ADR.

Default collection retains only context actually supplied for the task, subject to exclusions for known credential files, detected secrets, and project-configured exclusions. Do not snapshot the entire repository. Apply the same exclusion rules to experiment inputs and telemetry queues. Secret detection is imperfect, so explicit path exclusions remain necessary; this policy does not claim that automated detection finds every secret. Exact exclusion patterns, redaction representation, and enforcement at host and router boundaries remain implementation work.

### JD-072 — Missing context for experiment replay

Target: context and experiments RFCs.

When necessary context was excluded or never retained, mark the task unavailable for exact replay and request the specific missing context through the harness. If it cannot be supplied within applicable permissions and exclusions, skip exact replay while retaining permitted observational evidence. Do not silently recover excluded files or treat reconstructed context as equivalent to the original task. Requesting context does not itself override collection exclusions or authorize new access.

### JD-073 — Default routing deadline

Target: routing RFC and performance test plan.

Use a configurable five-second deadline for an ordinary routing request. Callers may request a longer deadline for complex tasks within governing limits. If JEV cannot complete in time, use a verified deterministic fallback or return a non-ready result. Five seconds is a provisional operating limit to validate against actual JEV and CLI latency, not a demonstrated performance guarantee. Exact timer boundaries and reserved time for fallback, validation, and durable recording remain to be specified; the deadline does not waive readiness or persistence requirements.

### JD-074 — Background resource priority

Target: experiments RFC and maintenance runbook.

Background experiments may run while the user is active only within configured resource limits. Interactive work takes priority. Stop launching background runs when the host reports contention; pause or cancel running work where supported. Immediate host-accepted bakeoffs retain their separate authorization. Resource budgets, contention signals, and pause/cancel mechanisms must be explicit; this decision does not claim every provider or host can pause an in-flight run.

### JD-075 — Regression rollback

Target: analysis RFC, release readiness, and recovery runbook.

When an automatic rollout breaches predefined regression criteria, stop expanding it, restore the previous policy for affected scopes, and notify the user. Preserve evidence for diagnosis. If the previous policy cannot meet current constraints, use a verified fallback or return non-ready. Suspend automatic promotion of the regressing version; a revised version must pass validation before promotion. Do not globally disable unrelated authorized promotion solely because one version regressed.

### JD-076 — Local analysis model enablement

Target: analysis and settings RFCs.

Run deterministic analysis by default. Local model-assisted analysis requires an explicitly enabled, verified analysis model and resource budget; discovering a compatible model does not enable its use automatically. Without a model, JEV Drill can still aggregate measurements, detect configured thresholds, and identify comparison opportunities. Model-assisted analysis remains subject to collection exclusions, project scope, and interactive-resource priority. This does not change separate external-provider or experiment authorizations.

### JD-077 — Dependency setup ownership

Target: inventory and integration RFCs.

Return structured setup proposals for missing dependencies, including local model downloads, container runtimes, and guidance tools. The host authorizes and performs setup under its existing authorization rules. JEV Drill rechecks readiness afterward. Routing and analysis do not silently install or download dependencies.

### JD-078 — Initial execution access routes

Target: integration RFC and roadmap.

Initially support execution routes already exposed by agent-harness, using its verified model inventory. Define a common access interface for direct provider APIs and local inference endpoints; implement those integrations in later stages. This execution-route scope is separate from the JEV routing-model connection. Inspect the harness to establish the exact supported route set rather than inferring providers from names or installed tools.

Owner exception on 2026-09-29: bring forward a bounded BAML direct-provider adapter solely for the approved development calibration pilot. Use already authorized providers, verified model identities and current raw rates. Reserve a conservative upper cost before each call; disable retries, fallback and extra calls. Enforce the approved per-experiment and whole-pilot caps. This does not authorize policy promotion or general direct-provider routing.

Owner continuation on 2026-09-30 permits implementing this adapter for explicitly configured development comparisons behind the experiment admission service. Bind purpose-built cases, model profiles, evaluator and raw rates before dispatch. A durable queue and separately invoked trusted worker must retain reservations and never repeat a call after an uncertain outcome. Use local provider fixtures for implementation verification. Paid enablement still requires a current explicit grant and budget; the original pilot allowance is not renewed. General direct-provider routing remains deferred.

### JD-079 — Initial experiment limits

Target: experiments and settings RFCs.

Once experiments are enabled, default to one background experiment at a time and two candidate plans per experiment. Require explicit time and compute limits before execution. External model calls require configured per-experiment and daily spending ceilings in addition to applicable provider authorization. Immediate bakeoffs also respect the host's remaining task budget and deadline. Propose numeric time/compute limits after inspecting the host; no universal hardware allowance is implied. These defaults do not themselves enable experiments, expand permissions, or prohibit later explicitly configured limits.

### JD-080 — Quality regression tolerance

Target: test plan and release readiness.

Default promotion requires no meaningful quality regression: meet each task family's quality floor and show that any loss stays within a predefined small tolerance. Insufficient evidence does not pass. Privacy, permission, and mandatory correctness checks cannot be traded for lower cost or latency. Users may explicitly authorize a different quality/cost tradeoff for a scoped optimization objective. Propose numeric tolerances with the evaluation design before held-out testing; this decision does not require zero observed loss on every individual task.

Owner clarification on 2026-09-29 for JD-080: promotion must introduce no additional critical failures. Calibrate other quality tolerances separately for implementation, review and documentation. Improvements in cost, speed or average quality cannot offset a new critical failure. Numeric tolerances remain an evaluation-design task and must be frozen before held-out testing.

### JD-081 — BAML for JEV calls


Target: integrations RFC and toolchain ADR.

Use BAML to call JEV, as explicitly requested after the interview. Isolate JEV call types and convert validated judgments through `integrations`. JD-082 subsequently changes public contract authorship to BAML where supported, with generated Pydantic types. Pin and verify a BAML toolchain supporting the TypeSafe client, including the Python interoperation path, before treating the integration as ready. Do not substitute a direct HTTP client without an explicit design change. The user-provided source is [BoundaryML's JEV integration announcement](https://boundaryml.com/blog/typesafe-ai-jev).

### JD-082 — BAML-authored public contracts where supported

Target: contracts RFC and toolchain ADR. Supersedes JD-008's handwritten Pydantic authority subject to capability verification.

Prefer one authored BAML contract source generating Pydantic and other required language types. Generated Pydantic models are consumers of that authority, not separately maintained field definitions. Generate portable JSON Schema through a verified export path. Preserve strict boundary validation, status-specific invariants, and generated-file consistency checks; BAML type generation alone is not proof of those behaviors. Keep JEV's narrower callable judgment types separate from general public contracts even when both are authored in BAML. Prove compatibility with the selected JEV-capable toolchain before freezing the implementation. If a necessary contract feature cannot be represented or generated, document the exact gap and propose the smallest explicit validation supplement rather than silently weakening a requirement or maintaining two competing schemas.

### BAML toolchain selection for JD-081 and JD-082

Use [`baml-language-0.20.1`](https://github.com/BoundaryML/baml/releases/tag/baml-language-0.20.1) as the initial compatibility-test pin, as accepted after repository inspection. The BAML v1 language toolchain still has a `0.x` release number; the installed legacy `0.226.2` is a different toolchain line. The selected release contains JEV adapter tests and a Python Pydantic 2 generator. Adoption requires proving contract generation, strict validation, JSON Schema export, and mocked JEV calls together on this exact toolchain. Record matching runtime dependencies and artifact checksums during that proof. Change the pin explicitly if verification reveals a blocking defect; do not silently follow canary or nightly builds. This selects the test baseline, not a claim of successful local installation or integration.

Subsequent verification: the [BAML proof](../research/baml-proof/README.md) demonstrates isolated generation, Python interoperation, schema export, mocked decoding, timeout behavior and one authorized live JEV call on this pin. Generated validation defaults do not satisfy JD-009; the strict validation supplement and remaining compatibility checks must pass before contract freeze. The original selection above describes the decision at selection time.

### JD-083 — Estimated routing and requested hard ceilings

Accepted by the user on 2026-09-29. Allow verified executors to participate in
estimated-cost routing without enforceable total-run token limits when no hard
execution spending or token ceiling is requested. Label estimates explicitly;
keep raw cost available and observed usage unknown until measured.

`execution_token_limits` names total input and output token ceilings for one
execution run, including every model call in that run. Context capacity and
per-call output limits do not establish these totals. A requested spending,
retry-spend or token ceiling requires compatible verified execution limits and
final host enforcement. Unknown rates cannot prove a spending ceiling; optional
subscription adjustments do not relax raw-token spending ceilings. This does
not relax JEV's own separate judgment-call budgets or experiment authorization.

### JD-084 — Linux workers for leased macOS execution

Accepted by the user on 2026-09-29. Use an explicitly configured Linux worker for
jobs that require leased worktree execution from macOS. Ordinary local macOS
routing and non-leased execution remain supported. Native macOS leased launch
must stop before executor startup or lease transfer, report
`native_macos_leased_execution_requires_linux_worker`, and recommend resuming on
the Linux worker. Do not silently move worktrees, credentials or permissions.

Native macOS acceptance verifies early rejection without executor side effects;
Linux acceptance verifies actual leased process-tree cleanup. Linux worker
execution is recorded as Linux evidence, never native macOS containment proof.
Automatic cross-machine provisioning or forwarding is outside this change.

## Intended adoption outputs

These are proposed target names/families, not files that have already been emitted:

| Target | Decision coverage |
|---|---|
| Product requirements (`prd`) | JD-003, JD-016–JD-018, JD-043, JD-046–JD-047 |
| Architecture (`c4_architecture`) | JD-003–JD-004, JD-007, JD-028, JD-045, JD-054, JD-064 |
| Implementation and component design (`rfc`) | JD-001–JD-045, JD-064–JD-079, JD-081–JD-082, as mapped above |
| Decisions (`adr`) | JD-058–JD-063, JD-068–JD-071, JD-081–JD-082 plus significant tradeoffs from the active decisions |
| Test plan (`test_plan`) | JD-017, JD-038, JD-041–JD-042, JD-047–JD-050, JD-073, JD-080 |
| Release readiness (`release_readiness`) | JD-007, JD-040, JD-051, JD-075, JD-080 |
| Roadmap (`roadmap`) and phase plans | JD-046, JD-052, JD-056, JD-065, JD-078 |
| Governance registry | JD-006, JD-052–JD-057 |
| Runbooks | JD-013, JD-044–JD-045, JD-066, JD-070, JD-074–JD-075 |

The pipeline owns adoption into `.pipeline/specs/`, sidecars, managed mirrors, and source manifests. These Markdown intake files do not claim those roles. Supporting reports are evidence, not requirements unless explicitly promoted. Preserve original research provenance and limitations.
