# Detailed plan: repair experiment contracts, JEV metering, and suitability calibration

## Task

Establish a trustworthy baseline before introducing GEPA. Repair demonstrable contract and measurement defects, and prepare an experiment that can distinguish useful suitability judgments from always admitting every model. Preserve the completed studies and their failed outcomes.

Planning was requested in Default mode. This artifact authorizes no implementation by itself; no tests, builds, generators, or paid calls ran during planning. Execute the three bounded work packages serially, each with its own evidence and closeout. This is a standalone repair plan, not acceptance of an entire roadmap phase.

## Research summary

The completed `evidence/EXPERIMENT/routing-comparison-20261005/` study recorded 300 executions, 120 ready product routes, and 240 JEV events. Cost routing passed 56/60 tasks, speed routing 59/60, and fixed Luna 60/60. JEV admitted every offered candidate. The public application already combines candidate models with supplied guidance options; it does not establish a complete standalone skill-discovery interface.

One remaining task ambiguity is concrete: `implementation-half-open-overlap` uses interval notation but omits the JavaScript array representation; an execution assumed objects. Returning the whole record in `implementation-last-correction` contradicts the supplied instruction and remains a model failure. Other failures include extra array nesting, altered example values, and one malformed JSON response. BAML converted nested arrays into strings in some review outputs, so successful typed parsing alone is insufficient evidence of faithful structure.

`usage-diagnostics.json` reproduces empty JEV event counters even with numeric usage in a loopback response. A nullable output counter raises a BAML error. The generated interface exposes both `ai.ModelTurn.usage` and `LLMCall.usage`; determining where usage disappears is a required implementation checkpoint. Do not assert that the live provider omitted usage: live bodies were not retained.

The first replay hash audit failed without recording the changed file. Original completed results kept their hash and later audits matched. Add diagnostic evidence for future discrepancies; leave the original limitation visible.

## Architecture and scope decisions

- Resource selection supplies guidance for the overall objective. The executive harness decomposes that objective and coordinates work. Each concrete task can request a separate model/effort/guidance execution plan.
- V0 resource selection should use objective relevance and required capabilities. Model choice then uses the concrete task and applicable guidance. Compatibility can require reconsidering a resource/model combination.
- Document these responsibilities in `docs/route-interfaces.md`. Do not create a new public skill-selection API in this repair. That requires its own bounded interface plan after an audit of the current catalog/handoff path.
- Keep deterministic permissions, budgets, readiness checks, and the no-additional-critical-failures rule. Prompt optimization cannot edit these rules or the grader.
- Do not install GEPA, optimize prompts, introduce confidence thresholds, promote policies, expose the release holdout, or publish changes as part of these repairs.
- Retain BAML for JEV calls and typed response contracts. Do not work around the bridge by switching production calls to a separate untyped HTTP implementation.

## Frozen contract and vocabulary obligations

`docs/vocabulary.yaml:7-10` states: “Accepted concept names are distinguished from proposed ownership and code forms”; “Deterministic usage checks cover declared identifiers and active documentation”; and “Contract field definitions belong in BAML under JD-082; this registry owns terminology.” Lines 12-16 prescribe `snake_case` modules/fields/functions, `PascalCase` classes, and forbid `utils`, `helpers`, and `common` module names.

`docs/jevdrill-spec.md:186-190` describes “domain → specialty → task → candidate descriptions → selected instructions” and requires JEV Drill's code to enforce feasibility and combine JEV judgments. Lines 194-198 require conservative accounting, bounded routing, and hard-constraint-preserving fallback.

No new public vocabulary, routing outcome, policy objective, or measurement unit is introduced. Use existing `resource`, `task`, `execution_plan`, `routing_decision`, and `measurement` concepts. Private experiment revisions and internal BAML helper identifiers are not new public protocol terms. Keep historical specification text intact; clarify current behavior in the active interface docs.

## Work package A: explicit task contracts and strict experiment validation

### Changes

- `research/evaluation/pilot/routing-contracts-v3.json` (create): versioned development task declarations. Audit all 20 exposed groups for argument representation, field names, null/empty behavior, ordering, mutation, and exact return shape. State intervals as two-element number arrays; state `.value` explicitly for records. Record an independent input schema and result schema per family, never infer the required schema from the model response. Preserve old fixture inputs and semantic expected answers; update documentation's expected wording only when its supplied wording changes. Mark all old groups exposed and ineligible for promotion.
- `scripts/verify_routing_contracts.py` (create): load and validate that dataset, generate private BAML task contracts using the existing comparison generator pattern, and validate raw structured responses before evaluating a BAML result. Use strict JSON parsing with duplicate-key/nonfinite rejection and strict schemas that reject extra nesting, unknown fields, and incorrect primitive types. Use BAML as the authored source for representable response types, with explicit companion constraints for argument tuple arity and semantic shape that BAML cannot represent. Assert schema derivation parity. Permit harmless whitespace/key-order changes, but reject structural coercion. Keep valid-but-wrong answers for independent semantic grading.
- `tests/verification/test_routing_contracts.py` (create): regressions for array/object mismatch, record-versus-value, nested-array-to-string coercion, serialized-object map keys, documentation argument corruption, malformed JSON, and correct controls. A structurally valid wrong answer must reach and fail the semantic grader.
- `.phase-loop/runs/PRE-GEPA-20261005/**` (create): private generated SDK, isolated transport workers, fixtures, and protocol preparation. Reuse the existing comparison harness through a new version; do not edit frozen historical runners or import two generated `baml_sdk` packages in one process.
- `evidence/EXPERIMENT/pre-gepa-20261005/contracts/**` (create): correction map, original/new digests, reference and negative-control outcomes, and schema parity evidence.

### Order and limits

First write the explicit declarations, then derive schemas/SDKs, then run the offline controls. A reference control must satisfy its own declared input/output contract before the dataset can be frozen. Historical failures remain historical failures. “Clearer wording improves accuracy” is a hypothesis until measured.

## Work package B: JEV usage capture through BAML

### Changes

- `baml_src/jev.baml` (modify): add an internal observation helper around the existing typed suitability specification. Inspect one direct `ai.ModelTurn` from the BAML client, capturing only the decoded Boolean, numeric usage, and timing needed by the adapter. Continue using BAML client construction, the supplied deadline, and disabled wire capture.
- `src/jevdrill/integrations/jev.py` (modify): consume the internal observation and preserve candidate/function/model binding, deadline enforcement, and the existing public `JudgmentRecord`. Return a redacted typed failure if the suitability value is invalid. Internal observation changes must not add a second provider invocation.
- `src/jevdrill/telemetry.py` (modify): project numeric observations from the verified source. Define precedence: direct turn usage is authoritative when present; use event usage only when direct usage is absent. Equal duplicate counters count once; conflicting counters become unknown with a recorded diagnostic. Do not sum call totals with their component events. Known zero remains zero; missing remains unknown. TypeSafe's free output pricing does not justify inventing an observed zero output count.
- `src/jevdrill/application.py` (modify only as necessary): attach the corrected numeric observations to the existing routing measurement fields once per call. Preserve measured costs separately from estimates and reservations.
- `tests/contracts/test_jev_boundary.py`, `tests/integrations/test_jev.py`, `tests/privacy/test_jev_privacy.py`, `tests/application/test_route_integration.py` (modify): actual loopback fixtures for numeric usage, zero, absent/nullable usage, duplicate/conflicting telemetry, malformed responses, cancellation, timeout, and exact replay without dispatch. Canary values in task text, headers, credentials, and response bodies must not appear in retained metadata.
- `docs/contracts.md`, `docs/route-interfaces.md` (modify): explain the actual implemented capture path, source precedence, missing counters, privacy, and the two-stage ownership boundary. Remove stale claims that the projection is not connected when the verified implementation is connected.
- `src/baml_sdk/**`, `schemas/**` (regenerate only through `scripts/check_generated_contracts.py --write`): inspect the generated diff; public schemas should remain unchanged. Never manually patch generated files.
- `evidence/EXPERIMENT/pre-gepa-20261005/metering/**` (create): fixtures, turn-versus-event observations, source hashes, and redaction evidence.

### Mandatory evidence checkpoint

Before changing the production adapter, run the same local numeric-usage fixtures through direct `ModelTurn` and existing event callbacks. If direct turn usage is intact, use the observation helper above. If both surfaces lose counters, or nullable usage fails inside the pinned client before the helper can observe it, stop package B with a reproducible upstream bridge blocker. Keep unknown accounting in place; do not fabricate a successful fix.

A compiler/runtime upgrade or custom replacement provider client is a separate bounded amendment because the current generator verifies a pinned artifact ABI and platform behavior. Record the exact failing fixture, compiler/runtime versions, and required behavior. This is an evidence-dependent stop condition, not an implementer's choice to weaken acceptance.

## Work package C: suitability calibration and a reliable fresh comparison

### Changes

- `research/evaluation/pilot/routing-calibration-v1.json` (create): 12 fresh related task groups with implementation, review, and documentation cases (36 cases). Keep every related variant in the same partition. Mark this corpus as development calibration; it is separate from the release holdout and must not become GEPA's final test set after exposure. Freeze concrete task requirements and independent expected outcomes before generation.
- `scripts/verify_routing_contracts.py` (extend): offline suitability fixtures with relevant candidate evidence, insufficient evidence, disallowed capabilities, local-only restrictions, and exhausted budget. Assert deterministic exclusions and that a negative JEV judgment cannot produce a ready plan. Fixtures identify orchestration behavior only; mock judgments cannot establish live JEV discrimination.
- `.phase-loop/runs/PRE-GEPA-20261005/**` (extend): prepare a five-arm comparison using the verified contracts and metering: fixed Groq, fixed Cerebras, fixed Luna, cost routing over Groq/Luna, and speed routing over Cerebras/Luna. Supply task-local guidance and family performance evidence with explicit source/exposure limits. Keep quality unknown until judged; never insert fabricated “measured sufficient” values. Keep the suitability prompt fixed for this baseline. GEPA may optimize it later against the frozen evaluation.
- `tests/verification/test_routing_contracts.py` (extend): durable reservation, uncertain-attempt nonretry, budget admission, partition separation, no answer leakage to JEV, and objective-specific mandatory-check regressions.
- `evidence/EXPERIMENT/pre-gepa-20261005/calibration/**` (create): frozen protocol, operational authorization record, ledger, decisions, typed outputs, independent grades, and objective analysis.
- `evidence/ROADMAP/latest-study.json` (modify after actual outcomes): point to the new preparation or completed result using its true status and retain previous study references. Original phase reducers and PREPARE status remain separate.

### Execution and evidence rules

Prepare everything offline first. Live execution is an explicit next action after the offline suite passes and package B supplies usable usage or a separately adopted runner amendment defines the limited unknown-cost study. This planning request is not a fresh paid-call authorization.

The prepared schedule is at most 180 execution calls and 144 JEV judgments, sequential, two candidates per route, no automatic retries, five-second routing deadline, 2,048 output-token cap, existing execution timeout, and the existing restricted grader limits of two CPUs and 2 GiB. Use only already authorized providers. Carry $0.845159775 committed or reserved into the inherited $2 guard; re-read the latest authoritative ledgers before admission. GEPA reflection-model spending is outside this schedule.

Unknown attempts retain their maximum reservation. Persist a dispatch record before each remote request. A replay must make zero external calls. For any changed hash, save the path, before/after hashes, and semantic SQLite table comparison; distinguish physical database representation changes from logical evidence changes. Compare an immutable snapshot, not a database with active writers. Never overwrite an old observation to make the audit pass.

Report additional mandatory failures against fixed Luna by task family, known and unknown cost, accepted-task cost only when complete, and latency including routing. Report suitability rejection rates and selection variation. All-true JEV responses are a calibration limitation, not successful discrimination. The baseline may still fail quality acceptance; the experiment runner can complete correctly while a policy remains ineligible.

## Verification

Run from the existing worktree with the repository `.venv`. Planned new command interfaces below are implementation requirements, not commands claimed to exist today.

```sh
.venv/bin/python -m pytest -q tests/verification/test_routing_contracts.py tests/contracts/test_jev_boundary.py tests/integrations/test_jev.py tests/privacy/test_jev_privacy.py tests/application/test_route_integration.py
.venv/bin/python scripts/verify_routing_contracts.py --contracts research/evaluation/pilot/routing-contracts-v3.json --calibration research/evaluation/pilot/routing-calibration-v1.json --offline --output evidence/EXPERIMENT/pre-gepa-20261005/offline.json
BAML_CLI=/mnt/workspace/worktrees/viperjuice/.baml-v1-0201-toolchain/bin/baml-cli .venv/bin/python scripts/check_generated_contracts.py
.venv/bin/python scripts/lint_vocabulary.py
.venv/bin/python -m pytest -q tests/contracts tests/application tests/privacy tests/integrations
git diff --check
```

automation.suite_command: .venv/bin/python -m pytest -q tests/verification/test_routing_contracts.py tests/contracts/test_jev_boundary.py tests/integrations/test_jev.py tests/privacy/test_jev_privacy.py tests/application/test_route_integration.py

The package B checkpoint is included in the boundary tests; an unavailable numeric observation must fail the metering acceptance test rather than be skipped. Run the narrow tests before regeneration comparison and broader integration checks. Do not run any verification during planning.

Operational evidence, if subsequently authorized, is `evidence/EXPERIMENT/pre-gepa-20261005/calibration/verification.json`. The execution runner must stamp a plan amendment with authorization reference, frozen protocol digest, current source digests, carried ledger commitment, limits, and actual outcomes before any downstream roadmap gate relies on it. Fixture or offline evidence is never a substitute for live evidence.

## Acceptance criteria

- [ ] Explicit input/output declarations cover all corrected groups and preserve semantic gold answers — proven by `scripts/verify_routing_contracts.py --contracts ... --calibration ... --offline --output ...` and `tests/verification/test_routing_contracts.py`.
- [ ] Structural coercion and malformed JSON fail while valid-but-wrong values reach independent grading — proven by `tests/verification/test_routing_contracts.py`.
- [ ] Known JEV usage survives one BAML invocation; zero, missing, duplicates, and conflicts have the specified meanings — proven by `tests/contracts/test_jev_boundary.py` and `tests/integrations/test_jev.py`; otherwise package B is blocked with a reproduction.
- [ ] No credential/task/body leakage, extra dispatch on replay, or weakened deadline/permission checks — proven by `tests/privacy/test_jev_privacy.py` and `tests/application/test_route_integration.py`.
- [ ] Generated code and existing public vocabulary remain consistent — proven by `scripts/check_generated_contracts.py` and `scripts/lint_vocabulary.py`.
- [ ] Fresh calibration groups, frozen criteria, durable reservations, and useful replay-failure diagnostics are ready offline — proven by the offline verifier and its targeted tests.
- [ ] Historical artifacts and inherited dirty work remain intact; docs accurately describe harness decomposition and the current API boundary — proven by the execution runner's starting/ending path-and-hash audit plus documentation review recorded in its closeout.
- [ ] Any later live result has machine-checked operational evidence and runner-stamped authorization; neither GEPA readiness nor policy promotion is inferred from a completed runner — proven by the adopted amendment and calibration verification artifact. Mark pending until live execution is separately authorized and actually completes.
