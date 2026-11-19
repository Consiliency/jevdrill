# Stopped calibration study review

Reviewed on 2026-10-09 by the parent agent and an independent fresh-context, read-only reviewer. This is an implementation and study-design review, not owner ratification or empirical phase acceptance. No credentials were accessed, provider calls made, source files changed, or grant replayed during this review.

Study: `discovery-development-proposed-20261009-v1`. Frozen source: `1b55174c7c906276e17708ba9edf337d0a8aee24d3690b8e8ae083be70a17ea3`.

The router's rejection was correct under its current contract. The recorded eight candidate IDs each received a false quality judgment and were excluded solely for `quality_unknown_or_insufficient`. No configuration was eligible. There is no observed transport, model-pin, Boolean-polarity, candidate-binding, or routing-transformation failure explaining those answers. The reason the model answered false was not retained and must not be inferred as measured candidate incapability. None of the candidate models produced an output.

1. **P1 — Reported JEV token telemetry is dropped, then aggregated under incompatible names.**

   `src/jevdrill/integrations/development.py:328-339` passes a `SimpleNamespace` to `jev_usage_measurements`; `src/jevdrill/contracts.py:261-264` accepts only the generated `JevUsageObservation` type. All fourteen actual call measurement lists contain only the separately appended `raw_token_cost`, although their response usage retains 13,736 input and 280 output tokens.

   Correcting that type alone is insufficient. The projector emits `routing_input_tokens` and `routing_output_tokens` (`contracts.py:266-290`), while `scripts/verify_discovery_calibration.py:476-497` searches judgment measurements for unprefixed `input_tokens` and `output_tokens`. Known combined totals therefore become `not_reported`. The validator recomputes the same helper (`801-804`) and permits missing counters (`459-466`), so this loss is not caught.

   Offline reproduction extracted the exact functions with Python AST, without importing JEV/BAML or making calls. A namespace event produced zero projected metrics; a nominal generated-observation stand-in produced three routing metrics. A known candidate input/output of 50/5 plus a known judgment of 100/10 produced missing totals instead of 150/15. This confirms the type guard and metric-name mismatch; the stand-in is not an end-to-end generated-SDK test.

   Fix the boundary projection and explicit navigation-to-objective metric mapping together. Add a real generated-observation test and an independent assertion of exact combined totals. Preserve genuinely unavailable cached-token counts as unknown. Recorded provider cost and separately measured navigation wall time remain available; this defect did not cause the all-false suitability result.

2. **P2 — The suitability question omits the instructions of the offered guided configuration.**

   `src/jevdrill/application.py:1032-1060` retrieves guidance text but uses it only for preparation/token counting. The public judgment row drops only `cost` (`745-747`); it carries guidance references/hashes and bookkeeping metadata, rather than the retrieved instructions. `baml_src/jev.baml:4` asks whether this “candidate meets the task requirements,” while the candidate is a prospective model execution profile, not an output. The driver explicitly sets `quality_sufficient=null`, unknown evidence strength and empty evidence references (`verify_discovery_calibration.py:1179-1182`).

   The task text does contain requirements; empty structured acceptance/context arrays do not prove that requirements were absent. Nevertheless, the question needs an explicit distinction between prospective task suitability and correctness of a produced answer, and the payload must represent the actual authorized execution configuration. Otherwise it cannot assess the contents of different guidance combinations. The contribution of this weakness to the eight false answers is unobserved.

   Define and render that judgment input, including only authorized task/context and precisely the offered guidance instructions. Test the request semantics and distinct configurations. Do not declare measured quality, fabricate priors, or force positive judgments.

3. **P2 — The simple-retrieval baseline may run without the retrieved guidance.**

   `scripts/verify_discovery_calibration.py:1265-1277` installs lexical retrieval results as optional `guidance_options`. Candidate expansion always includes the empty combination (`application.py:1008-1010`), and raw token-cost minimization can prefer it when both guided and unguided configurations pass suitability (`routing.py:232-236`). The baseline validator merely checks that executed resource IDs appear in the objective (`verify_discovery_calibration.py:818-820`); an empty list passes vacuously.

   This is a downstream code-path finding, not something executed in the stopped run. The loopback driver test uses only the first case (`tests/verification/test_discovery_calibration.py:296`), whose objective is “shared” and retrieves no resource. Make arm construction and validation enforce the preregistered retrieval baseline. Add a nonempty-retrieval case and assert the executed configuration contains exactly the prescribed admitted resources.

4. **Study-design limitation — Calibration depends on a prior positive suitability result and does not record abstention as a case outcome.**

   All candidate quality priors start unknown. The driver raises on a non-ready actual route (`verify_discovery_calibration.py:1234-1235`) before baseline execution, grading and case-row recording. This occurred on the first case, leaving zero completed cases and comparisons. Rejected configurations therefore provide no downstream data about false-negative suitability decisions, and one abstention prevents collection of later cases.

   This is not a deterministic proof that every unknown candidate must fail; JEV could return true. It is a fragile collection prerequisite and a limitation of the planned experiment. Preserve the abstention and its route/discovery/call lineage as a first-class partial outcome. If evaluating rejected configurations is necessary, prepare a separately reviewed development-only sampling design and fresh authorization. Do not weaken production admission or reuse this grant.

   The observed discovery selected `bounds` plus `pure-contract`, while this case's preregistered acceptable set contains only `bounds`. That is an exact-set benchmark mismatch, not a measured downstream critical failure. Review the oracle's treatment of compatible additional guidance before a new protocol is frozen; do not change the historical expected set retrospectively.

The successful loopback tests return unconditional JEV probability 0.9 (`tests/experiments/test_development_judge.py:34`; `tests/verification/test_discovery_calibration.py:308-315`). They establish transport and happy-path orchestration, but do not verify the task-judgment semantics, all-false partial recording, known combined token totals, or nonempty retrieval execution.

Recommended next work: make a bounded offline correction plan for telemetry, judgment inputs, retrieval-arm fidelity and abstention recording; verify those changes with meaningful targeted tests. Then freeze a revised protocol and source, retaining all prior evidence, before requesting any new paid collection. Whether an exploratory qualification arm is needed remains a separate design decision. No new quality floors or tolerances have been selected by this review.

Evidence inspected: `study-run-stop-diagnostic.json`, `study-run-public-quality-context.json`, `study-run-closeout.json`, `study-run-validation.json` and the immutable study artifacts. Their hashes and the three recorded database hashes matched the validation record. The original disabled preview and original EXPERIMENT closeout retain their recorded hashes. EXPERIMENT remains blocked; no phase gate or PREPARE authority is produced by this review.

