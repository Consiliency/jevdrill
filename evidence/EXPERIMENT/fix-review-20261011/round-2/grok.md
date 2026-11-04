R1–R4 hold on the frozen round-2 tree. D1 is still an owner decision and still blocks the next source freeze. This review does not accept empirical candidate quality.

The head manifest `13ffc320fbacec67cf6627e5c98a7ccbc0fc6d90ece00b68e385d90603ef6dfd` matches `delta-binding.json`, and all twelve manifest hashes matched the worktree before and after the checks. `baml_src/jev.baml` and the three generated SDK hashes are unchanged from `study-defect-fixes-20261010.json`. No source or evidence was edited.

Tests executed:

- `BAML_CLI=/home/viperjuice/workspace/worktrees/route-compiler-0.20.1/bin/baml-cli .venv/bin/python scripts/check_generated_contracts.py` returned `{"passed": true, "generated_files": 147, "schemas": 78, "write": false}`.
- `.venv/bin/python -m pytest` on `tests/experiments/test_development_judge.py`, `tests/application/test_route_integration.py`, `tests/contracts/test_jev_boundary.py`, `tests/verification/test_discovery_calibration.py`, and `tests/integrations/test_jev.py`: 97 passed in 115.08s.
- One temporary offline probe routed two task-required resources plus two unselected options. It is not part of the suite.

The full suite was not run here.

## Closed routine corrections

**R2.** The judged object is an allowlist at `src/jevdrill/application.py:745-779`. `guidance_options`, `cost`, `rates`, `default`, `source`, `supported_efforts`, and `token_counter_revision` are outside it. The internal row still expands the menu at `src/jevdrill/application.py:1042-1050`; the worker plan keeps only selected refs at `src/jevdrill/routing.py:279-289`. `tests/application/test_route_integration.py:271-317` pins the emitted key set, four distinct instruction tuples, and the absence of each unselected option’s id, revision, hash, and role. Lines 318–322 compare a cleared-options route, on a separate database, with the unguided rows from the populated route. On an honest driver arm, `tests/verification/test_discovery_calibration.py:481-484` records no new judgment calls for `no_guidance` or `fixed_default`. Those baselines stay `ready` with `quality_sufficient` left unknown, so the empty call lists are receipt reuse. The prompt file hash is unchanged.

The same probe, with `execution_token_limits` present, judged that limit and no forbidden menu or price key. Its required and optional refs equaled the execution plan. Stripping `token_count` left those two required refs equal to the validator’s task-required recipe. The suite fixture omits `execution_token_limits`, so the pinned key set at `tests/application/test_route_integration.py:272-298` does not mention it. The allowlist at `src/jevdrill/application.py:765` passes it through, and the study profile sets it at `scripts/verify_discovery_calibration.py:1208`. It is a candidate limit used by `src/jevdrill/routing.py:120-122`, not the expansion menu.

**R4.** `scripts/verify_discovery_calibration.py:720-728` builds the task-required set from the frozen discovery and route fixtures, drops recomputed `token_count`, and forces the route `task_id`. Lines 822–855 require empty optional guidance on all four baselines, required guidance equal to that set on the three non-retrieval arms, and required guidance equal to the catalog-ordered lexical refs on `simple_retrieval`. Lines 1296–1313 preserve the actual plan’s required guidance for non-retrieval arms and install only the prescribed lexical refs for `simple_retrieval`. The error text remains `baseline does not implement its preregistered selection condition`.

`tests/verification/test_discovery_calibration.py:287-299` and 393–461 pin the exact validator error set. Case 3’s objective contains `bounds` and not `review-integrity`. Omission, substitution, and an extra resource are asserted on the executed retrieval plan at lines 471–480. `no_guidance`, `fixed_default`, and `cheapest_feasible` each receive one injected required ref. Honest case 0, whose objective contains no resource id, expects retrieval reuse.

Residual coverage: the `optional` mutation also clears required guidance, and line 479 expects an empty executed set. On case 3 that already fails `required != retrieved`, so this case does not isolate the optional-empty clause. The clause is present at lines 839–841. Substituted, extra, and per-arm injected-required mutations do isolate their conditions.

**R1 and R3**, checked with the same run. `src/jevdrill/integrations/development.py:349-350` emits `not_reported`. `tests/experiments/test_development_judge.py:148-189` covers absent usage, `{}`, null input with known or zero output, and both null, for task and discovery records, then replays with two dispatches and two retained reservations. Unknown `raw_token_cost` still fails study telemetry at `scripts/verify_discovery_calibration.py:451-453` and 895–898. `tests/application/test_route_integration.py:239-262` satisfies the synthetic requirement in the test candidate. False judgments produce four `quality_unknown_or_insufficient` exclusions through `src/jevdrill/routing.py:145-149`; the true counterfactual becomes `ready`.

## D1 still pending

Judgment semantics stay on `JudgeCandidate-v1` at `baml_src/contracts.baml:154` and `:164`, `src/jevdrill/integrations/development.py:410`, and `scripts/verify_discovery_calibration.py:1189`. The judge revision at `src/jevdrill/integrations/development.py:159-175` and the route cache digest at `src/jevdrill/application.py:604-613` still omit the request template. `docs/route-interfaces.md:75-79` still describes the discovery payload only. `evidence/EXPERIMENT/fix-review-20261011/round-1/judgment-version-amendment-proposal.json:2` is `proposed_owner_decision`. No v2 bump and no template binding landed. D1 remains the source-freeze blocker.

No paid call, grant reuse, collection-policy change, or empirical acceptance is implied. The guarded driver answers suitability with loopback probability 0.9.

PARTIALLY AGREE
