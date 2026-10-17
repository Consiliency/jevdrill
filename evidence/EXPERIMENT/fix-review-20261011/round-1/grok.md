The bound sources match the round-1 manifest. The honest authorized path projects JEV token counts once, sends the selected guidance texts, and installs lexical retrieval as required guidance. Two contract holes remain: the suitability payload is wider than the executed profile, and baseline validation still accepts guided plans for the no-guidance arms.

## Blockers

**High. FIX-2.** The suitability candidate is the whole prepared row except `cost`, so it still carries `guidance_options`, the full optional menu, while the executed profile is only `required_guidance` plus `optional_guidance`.

Trigger: `_prepare` shallow-copies the candidate, expands optional combinations, and then sets the selected refs and `guidance_instructions` without removing `guidance_options` (`src/jevdrill/application.py:1010-1018`, `src/jevdrill/application.py:1074-1075`). The judge receives that object (`src/jevdrill/application.py:745-748`, `src/jevdrill/integrations/development.py:400-401`). The plan and the worker execute only the selected refs (`src/jevdrill/routing.py:279-290`, `src/jevdrill/integrations/development.py:696-711`).

Consequence: a combination that executes only “first” is still judged with the “second” resource id, revision, and hash on `guidance_options`. Instruction bodies of unselected resources are absent, and the four instruction tuples differ, but the judged configuration is not the executed one.

Repair: send a projection of model, effort, capabilities, limits, selected refs, and `guidance_instructions`, and add a test that an unselected option id is absent from the judged JSON.

**High. FIX-3.** Selection validation does not enforce the non-retrieval baselines.

`validate_study` rejects those arms only when `optional_guidance` is nonempty, the fixed-default model id is wrong, or `no_guidance` disagrees on model or effort (`scripts/verify_discovery_calibration.py:813-838`). `required_guidance` is unchecked. `cheapest_feasible` has no cost or model check. `configured_worker_errors` rebuilds the prompt from whatever refs are on the plan (`scripts/verify_discovery_calibration.py:627-638`), so a bundle that puts required guidance on `no_guidance`, `fixed_default`, or `cheapest_feasible` stays internally consistent and does not raise “baseline does not implement its preregistered selection condition.”

The authorized constructor does clear `active_guidance` for those arms and puts lexical hits only on `simple_retrieval` (`scripts/verify_discovery_calibration.py:1279-1292`). Honest runs match. The validator can still accept a different executed set.

`simple_retrieval` id equality does reject omitted, substituted, and extra ids, and the worker hash check ties instruction text to the protocol corpus.

Repair: require both required and optional guidance to be empty for the three non-retrieval arms; for `cheapest_feasible`, re-derive the minimum-cost model from the frozen rates. Add a forged-artifact test.

## Medium

**FIX-1.** Honest calls are charged once. `DevelopmentJudge` builds a real `JevUsageObservation` (`src/jevdrill/integrations/development.py:328-339`). The projector emits one `routing_input_tokens` and one `routing_output_tokens`; equal direct and call counters collapse to one value; `0` stays known; a missing counter stays `not_reported` (`src/jevdrill/contracts.py:261-300`). `objective_tokens` adds candidate `input_tokens`/`output_tokens` to judgment `routing_*` counters (`scripts/verify_discovery_calibration.py:476-504`).

The validator does not enforce that once. It sums every listed judgment id and every matching metric row. Duplicate ids inside one arm pass the set intersection and the later set equality (`scripts/verify_discovery_calibration.py:787-812`, `scripts/verify_discovery_calibration.py:902-904`) and are added twice. Duplicate `routing_input_tokens` rows in one call payload are also summed. The driver currently stores a set of ids and one projected row, so a normal run does not double-charge.

Repair: reject duplicate call ids and more than one row per metric per call.

Cached usage stays unknown when a judgment has no `routing_cached_input_tokens`. The projector has no cached field, and `retain_jev_call` forces `cached_input_tokens` to `None` for `JevUsageObservation` (`src/jevdrill/telemetry.py:15-26`). A known candidate cached count, including zero, therefore becomes `not_reported` in the objective total whenever a judgment is included. That matches the unit test and the “unavailable stays unknown” rule.

## What holds

The task payload sent to suitability is task, acceptance, attachment refs under `context`, and governing refs (`src/jevdrill/application.py:751-763`). `IsSuitable` asks about prospective configuration suitability and says unknown quality is not measured quality (`baml_src/jev.baml:2-4`). A false judgment is stored and then excluded because feasibility requires `quality_sufficient is True` (`src/jevdrill/routing.py:145-146`). The route test covers four distinct instruction tuples and the absence of an unoffered instruction body.

The authorized `simple_retrieval` arm copies the first two catalog resources whose ids occur in the objective into `active_guidance` and clears `guidance_options`. The loopback test includes protocol case 3, whose only literal hit is `bounds`.

Reviewed fix surfaces do not add PREPARE authority, grant reuse, or a collection-policy change. Routing abstention still stops baseline collection; that remains out of scope.

## Verification scope

Manifest hashes match `study-defect-fixes-20261010.json`. This review did not re-run the claimed 84 targeted tests or the 828-test suite. The retrieval and token tests use loopback or synthetic measurements. The guarded driver returns JEV probability 0.9, so it does not show false suitability inside the study. Its `validate_study` assertion only requires three expected error strings to be present (`tests/verification/test_discovery_calibration.py:416-420`); additional validator errors would still pass. None of this is empirical candidate-quality evidence.

## Limitations

`offline()` still clears optional guidance, routes with the fixture’s empty `active_guidance`, and records `guidance` as the lexical id list (`scripts/verify_discovery_calibration.py:234-259`). That diagnostic cannot pass `validate_study`.

On this protocol the literal `id in objective` rule never selects `review-integrity`, `api-docs`, or `pure-contract`. Every nonempty case selects only `bounds`, including inside `array-bounds` and the word “bounds”. The two-id cap is not exercised.

PARTIALLY AGREE
