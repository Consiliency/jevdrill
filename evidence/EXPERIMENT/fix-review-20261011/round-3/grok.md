No blocker. The owner-approved v2 amendment closes D1 and both carried pre-freeze repairs, and R1–R4 stay closed. This is scoped review evidence only. The loopback oracle is probability 0.9. It is not an empirical measurement, a study grant, or merge or deploy authorization.

## Prior items

**D1 — closed.** Live task judgment is `JudgeCandidate-v2`. Historical `JudgeCandidate-v1` still parses and replays without dispatch. `ObserveDiscoveryOption-v1` stays a separate constant.

**Fixture source binding — closed.** `source_digest` hashes raw bytes of `tests/contracts/fixtures/discovery.json` and `route-application.json`. A post-run newline on each copied fixture is rejected and then restored.

**Optional-guidance isolation — closed.** On case 3 (`durable-queue-implementation`), the optional fault keeps the prescribed required retrieval ref `bounds` and adds a different feasible optional ref, `review-integrity`. The unmutated case passes. The baseline error on the optional fault comes from the non-empty optional clause.

**Projection coverage — closed.** One shared 26-field set is projected, bound, and asserted, including populated `execution_token_limits`. Unselected id, revision, hash, and role stay out of the judged row.

**`cheapest_feasible` receipt reuse — closed.** Case 0 with no fault pins an empty judgment-call list beside `no_guidance` and `fixed_default`.

**R1–R4 — remain closed.** Unknown cost still emits `not_reported`. False judgments still exclude on `quality_unknown_or_insufficient`. The baseline comparison is unchanged and still matches full refs except `token_count`.

**F6, F7, and D2–D6 — unchanged.** They are broader study-design questions and are outside this delta.

## V2-1 through V2-4

**V2-1.** `baml_src/contracts.baml:154` and `:164` accept the v1|v2 literal. `src/jevdrill/integrations/jev.py:25` sets the live label to v2. `JevAdapter.judge` rejects v1 at `jev.py:114-115`. `Application.route` rejects it before the injected judge at `application.py:751-754`. Same-key replay returns the stored decision at `application.py:570-609`. A new idempotency key with a v1 policy returns `routing_failed` and leaves the stored bundle unchanged (`tests/application/test_route_integration.py:306-367`). Discovery policy remains `const` `ObserveDiscoveryOption-v1` at `schemas/DiscoveryJudgmentPolicy.json:109-112` and rejects both JudgeCandidate labels.

**V2-2.** `judgment_template_binding` at `jev.py:59-67` digests the rendered `candidate_request_shape("<task>", "<candidate>")` body plus the sorted field names and projection version. `development_judgment_template_binding` at `jev.py:70-78` also digests the pinned development task and discovery renders. That binding is spread into the development profile revision (`development.py:160-176`), the validator expectation (`scripts/verify_discovery_calibration.py:676-691`), and the product cache digest (`application.py:613-623`). An incompatible profile raises `development_judgment_profile_changed` before the profile row is replaced (`development.py:186-189`). Durable replay also compares the stored and current rendered request digests (`development.py:244-270`). Five profile drifts and a changed rendered body are pinned in `tests/experiments/test_development_judge.py:149-219`. Cache reuse and template, projection, and field-set invalidation are pinned in `test_route_integration.py:370-421`.

**V2-3.** Digest patterns are at `verify_discovery_calibration.py:321-327`, compared at `:705-709`. The copied-fixture newline check is at `tests/verification/test_discovery_calibration.py:524-538`. Because the authority preview embeds `source_digest` (`verify_discovery_calibration.py:387` and `:415-421`), that newline also reports authority and exposure mismatch. Restoring the bytes returns the original error set. The optional mutation is at `test_discovery_calibration.py:412-448`, with the plan pin at `:494-498` and the clause at `verify_discovery_calibration.py:845-848`. The 26-key pin, exact selected instructions, and absent unselected identity fields are at `test_route_integration.py:206-210` and `:277-297`. The projection filter is `application.py:760-766`, using `JUDGMENT_CANDIDATE_FIELDS` from `jev.py:27-56`.

**V2-4.** `development.py:353` still records unknown cost as `not_reported`. `routing.py:145-146` still excludes when quality is not true. The baseline predicate at `verify_discovery_calibration.py:845-862` was not edited. The seven schema diffs replace only `function_revision: const JudgeCandidate-v1` with an `anyOf` of v1 and v2: `JudgmentPolicy.json:112-116`, `JudgmentRecord.json:185-189`, `RouteInputs.json:840-844`, `DiscoveryRouteInputs.json:867-871`, `ReplayBundle.json:735-739`, `RecoveryDecision.json:775-779`, and `RecoveryBundle.json:1005-1009`. Docs and the ROUTE freeze record the amendment at `docs/contract-decisions.md:27-36`, `docs/route-interfaces.md:86-97`, and `plans/phase-plan-v1-ROUTE.md:157-160`. No collection, provider-allowance, attribution, or holdout file is in the 27-file delta.

## Checks

Before any command, all 243 manifest paths matched `round-3/source-manifest.json`. The manifest SHA-256 is `d6277cc6e06151bbe8b7fe798f6b80150e3bda0211ca31edf17cec0fccb8eab8`. `base-manifest.json` is `9cf16b002fa9e6f901380abdc24f2ac7b71f1186812c017907dfc9fb1c2ca656`. `correction-base` matches that base for all 243 paths. The same 243 head hashes matched again after the checks.

Focused pytest, with bytecode and pytest cache writes disabled: **130 passed in 45.57s**. Pinned generation parity, `write=false`: **passed, 147 generated files, 78 schemas**. Node Ajv on `tests/contracts/fixtures`: **197 fixtures, exit 0**. v1 and v2 judgment fixtures accept with the recorded digests. v3 rejects. No source, evidence, or index file was edited.

## Limits

The full configured suite, ruff, mypy, and the offline package build were not run here. No macOS or Windows run was made. Historical study databases and the consumed grant were not opened. Profile refusal is the code path and the synthetic drift test. The product cache binds the placeholder render of `candidate_request_shape`, which is the approved template binding. The rendered body includes the suitability prompt and both placeholders.

AGREE
