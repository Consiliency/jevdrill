# Review Verdict: PARTIALLY AGREE

**Review Subject**: [`plans/detailed-pre-gepa-repairs-20261005-1336.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md)  
**Charter**: [`research/pre-gepa-review/brief.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/brief.md)  
**Lens**: Alternatives and Experimental Validity  

---

## Executive Summary

The repair plan is sound in its serialization (Package A → Package B → Package C), its adherence to owner decisions (BAML retained as the call/contract mechanism, executive harness decomposition, GEPA deferred, no additional critical failures allowed for policy promotion), its budget discipline (carrying $0.845 committed/reserved under the $2 guard), and its evidence-dependent stop condition for BAML bridge limitations.

However, the plan cannot be agreed to without reservations (**PARTIALLY AGREE**) because it contains critical experimental validity gaps and contract telemetry inconsistencies:
1. **Degenerate Experimental Control**: The plan aims to "distinguish useful suitability judgments from always admitting every model," yet fixes the zero-shot JEV prompt and offers candidate pairs that JEV previously admitted 100% of the time, guaranteeing that the routed arms collapse identically into fixed Groq and fixed Cerebras.
2. **Telemetry Invariant Disconnect**: [`JudgmentRecord.measurements`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/contracts.baml#L221) is left empty in [`src/jevdrill/integrations/jev.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/integrations/jev.py#L105), disconnecting JEV call measurements from durable replay bundles.
3. **Confounding in Paired Critical Checks**: Single-draw non-deterministic completions without fixed sampling temperature confound model stochasticity with routing regressions.

---

## Blocking Findings

### Finding 1 (Blocker): Suitability discrimination cannot be calibrated or validated using an unchanged zero-shot prompt with uniformly suitable candidates
* **Impacted Plan Sections**: Line 5, Line 75, Line 88.
* **Bound Acceptance Criteria / Invariants**:
  * Plan AC: *“Fresh calibration groups, frozen criteria, durable reservations, and useful replay-failure diagnostics are ready offline”* (Line 116).
  * Invariant: `docs/jevdrill-spec.md:186-190` & `JD-080`: Suitability must protect a quality floor and enforce feasibility.
* **Defect / Validity Gap**:
  Line 5 declares the objective to *"prepare an experiment that can distinguish useful suitability judgments from always admitting every model."* However, Line 75 specifies *"Keep the suitability prompt fixed for this baseline."* In the completed study ([`summary.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/summary.md#L23-L28)), JEV admitted 100% of offered candidates (240/240 calls), causing `route-cost` to pick Groq 60/60 times and `route-speed` to pick Cerebras 60/60 times.
  On the new 36 calibration cases, offering only Groq/Luna and Cerebras/Luna with the exact same zero-shot prompt will predictably yield 144/144 admissions. Line 88 concedes: *"All-true JEV responses are a calibration limitation, not successful discrimination."*
  Executing live arms under these conditions does not test adaptive routing or discriminate suitability; it re-executes fixed Groq and Cerebras under a 500 ms routing overhead penalty.
* **Minimal Repair**:
  1. **Offline Discrimination Invariant**: Extend the offline suitability test suite in [`scripts/verify_routing_contracts.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/scripts/verify_routing_contracts.py) to include explicit negative controls (candidates with missing capabilities, insufficient context limits, or unsupported operations). Require AC 116 to assert that negative controls receive `quality_sufficient: false` and are excluded from ready plans.
  2. **Refactor Stated Baseline Objective**: Amend Line 5 and Line 75 to explicitly designate this baseline comparison as an *uncalibrated control baseline* to measure baseline all-true rates and downstream error propagation, rather than claiming it can "distinguish useful suitability judgments."

---

### Finding 2 (Blocker): JEV telemetry capture omits measurements from `JudgmentRecord`
* **Impacted Plan Sections**: Lines 54–59, Lines 105, 113.
* **Bound Acceptance Criteria / Invariants**:
  * Plan AC: *“Known JEV usage survives one BAML invocation; zero, missing, duplicates, and conflicts have the specified meanings — proven by `tests/contracts/test_jev_boundary.py` and `tests/integrations/test_jev.py`”* (Line 113).
  * Invariant: [`baml_src/contracts.baml:221`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/contracts.baml#L221) defines `JudgmentRecord.measurements: Measurement[]`. [`docs/route-interfaces.md:30`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/route-interfaces.md#L30) specifies that `ReplayBundle` retains `JudgmentRecord` without external provider calls.
* **Defect**:
  In [`src/jevdrill/integrations/jev.py:105`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/integrations/jev.py#L105), `JevAdapter.judge()` hardcodes `"measurements": []`. In [`src/jevdrill/application.py:340-360`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/application.py#L340-L360), measurements collected by the callback are attached to `decision["details"]["measurements"]`, but `JudgmentRecord` remains unpopulated in [`ReplayBundle.judgments`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/application.py#L384).
  WP B describes feeding observations into `telemetry.py` and `application.py`, but does not mandate updating `JevAdapter.judge()` to attach sanitized `Measurement` objects directly to `JudgmentRecord.measurements`. Any offline replay audit inspecting `ReplayBundle.judgments` would find empty measurements.
* **Minimal Repair**:
  Add an explicit requirement to WP B that `JevAdapter.judge()` attaches sanitized numeric measurements to `JudgmentRecord.measurements`. Bind AC 113 to assert that both `decision["details"]["measurements"]` and `bundle["judgments"]["measurements"]` contain identical projected measurements.

---

### Finding 3 (Blocker): Paired critical regressions are confounded by single-draw sampling non-determinism
* **Impacted Plan Sections**: Line 75, Line 84, Line 88.
* **Bound Acceptance Criteria / Invariants**:
  * Plan AC: *“Any later live result has machine-checked operational evidence and runner-stamped authorization; neither GEPA readiness nor policy promotion is inferred from a completed runner”* (Line 118).
  * Invariant: `docs/vocabulary.yaml:76-80`: `critical_regression` blocks policy promotion if a critical requirement passed by baseline is failed by candidate on the same paired case.
* **Defect / Validity Gap**:
  In [`evidence/EXPERIMENT/routing-comparison-20261005/objective-analysis.json`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/objective-analysis.json#L236-L246), Cerebras failed `review-duplicate-key-counts` in the fixed arm but passed in the routed speed arm, while Groq failed `bounded-batch` in the fixed arm but passed in the routed cost arm.
  Under single-sample execution per arm, stochastic failures are conflated with systematic routing policy degradation.
* **Minimal Repair**:
  1. Mandate greedy decoding (`temperature: 0` or provider-equivalent deterministic seeds) in `.phase-loop/runs/PRE-GEPA-20261005/**` request configs.
  2. Report individual model failure distributions across all 5 arms in `objective-analysis.json` so that intrinsic candidate model failures are isolated from routing selection errors.

---

## Recommendations & Alternatives

### Recommendation 1 (Alternative): Decouple strict raw response validation from BAML code generation
* **Analysis**:
  WP A proposes using BAML as the authored source for task response types, generating a private SDK, and generating companion constraints for types BAML cannot represent (e.g. interval tuple arity `[number, number]`).
  Because the pinned compiler fixes its Python import namespace to `baml_sdk` ([`docs/contracts.md:5`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/contracts.md#L5)), maintaining dual SDKs requires subprocess isolation and custom parity generators.
* **Alternative**:
  Author task output contracts directly as JSON Schema (Draft 2020-12) in `routing-contracts-v3.json`. Validate `turn.terminal_text()` directly using `Draft202012Validator` before any evaluation. Use BAML purely for prompt execution (single turn completion). This eliminates BAML type coercion risk without requiring a synthetic private BAML schema generator.

### Recommendation 2: Pre-specify the "Unknown-Cost Study" amendment template
* **Analysis**:
  [`usage-diagnostics.json`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/usage-diagnostics.json) demonstrated that BAML 0.20.1's Rust runtime emits empty usage for TypeSafe AI `/systemone` loopback responses and crashes on nullable output tokens. There is a strong likelihood that direct `ai.ModelTurn.usage` also drops counters.
  Line 65 requires stopping Package B with an upstream blocker.
* **Recommendation**:
  Pre-define the schema and criteria for the "limited unknown-cost study" runner amendment in WP C so that if the Package B checkpoint halts on bridge limitations, offline preparation for WP C can proceed without stalling the development cycle.

### Recommendation 3: Calibration Partition Sizing
* **Analysis**:
  The proposed 12 groups (36 cases across 3 families = 12 cases/family) offer very low statistical resolution (1 failure = 8.3% error rate).
* **Recommendation**:
  Ensure the 12 fresh groups explicitly sample known boundary conditions (intervals, nested records, duplicate keys) observed in the pilot failures, ensuring maximum test coverage across the 36 cases.

---

## Files Actually Read

1. [`research/pre-gepa-review/brief.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/brief.md)
2. [`plans/detailed-pre-gepa-repairs-20261005-1336.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md)
3. [`evidence/EXPERIMENT/routing-comparison-20261005/summary.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/summary.md)
4. [`evidence/EXPERIMENT/routing-comparison-20261005/usage-diagnostics.json`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/usage-diagnostics.json)
5. [`evidence/EXPERIMENT/routing-comparison-20261005/protocol.json`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/protocol.json)
6. [`evidence/EXPERIMENT/routing-comparison-20261005/objective-analysis.json`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/objective-analysis.json)
7. [`baml_src/jev.baml`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/jev.baml)
8. [`baml_src/pilot.baml`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/pilot.baml)
9. [`baml_src/review_pilot.baml`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/review_pilot.baml)
10. [`baml_src/contracts.baml`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/contracts.baml)
11. [`baml_src/boundary.json`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/boundary.json)
12. [`src/jevdrill/integrations/jev.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/integrations/jev.py)
13. [`src/jevdrill/integrations/pilot.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/integrations/pilot.py)
14. [`src/jevdrill/telemetry.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/telemetry.py)
15. [`src/jevdrill/application.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/application.py)
16. [`src/jevdrill/contracts.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/contracts.py)
17. [`tests/contracts/test_jev_boundary.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/tests/contracts/test_jev_boundary.py)
18. [`scripts/check_generated_contracts.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/scripts/check_generated_contracts.py)
19. [`docs/contracts.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/contracts.md)
20. [`docs/route-interfaces.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/route-interfaces.md)
21. [`docs/vocabulary.yaml`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/vocabulary.yaml)
22. [`.phase-loop/runs/ROUTING-comparison-20261005/prepare.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/ROUTING-comparison-20261005/prepare.py)
23. [`.phase-loop/runs/ROUTING-comparison-20261005/controls.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/ROUTING-comparison-20261005/controls.py)

