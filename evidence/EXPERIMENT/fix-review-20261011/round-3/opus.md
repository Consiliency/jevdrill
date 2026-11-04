# Round 3 delta review: Opus seat (correctness and schema compatibility)

**Bottom line:** the v2 amendment closes D1 and both carried blockers, R1–R4 still hold, and I found no code defect. Two cheap items remain before the freeze:
- **O1 (low):** the projection test can no longer catch a pricing key being added to the shared field constant.
- **O2 (verification obligation, not a code defect):** `docs/contract-decisions.md:23` requires the OS matrix to be rerun for any amended contract, and it hasn't been.

## What I ran

**Hashes**
- **Before:**
  - `source-manifest.json` is `d6277cc6…eab8` and `base-manifest.json` is `9cf16b00…a656`, matching the brief and `delta-binding.json`.
  - Both list the same 243 paths, and every current file matches the frozen hash (aggregate `8d652122…8f1d`). `correction-base/` matches the base manifest (`61c2d525…9977`).
  - Base and head differ in exactly the 27 files in `delta-binding.json`. Both validator fixtures are byte-identical to round 2.
- **After all runs:** the aggregate is still `8d652122…8f1d` and the manifest is still `d6277cc6…`. Nothing under `evidence/`, `research/`, `tests/contracts/fixtures/` or `schemas/` (outside the review folder) is newer than the round-3 manifest.
- **Stopped-study `judgments.db`:** sha256 `be59fa07…2914`, dated Oct 9. I byte-scanned it and the `judgment_profile` table text is present, but I did not open it as a database.

**Commands**

| Check | Result |
|---|---|
| The six prescribed focused files | 130 passed (46 s) |
| Contract tests incl. the Node consumer over every fixture file | 150 passed |
| Generation parity | `{"passed": true, "generated_files": 147, "schemas": 78, "write": false}` |
| Full `tests/` with the pinned `BAML_CLI` | 894 passed, 12 failed, 7 errors (158 s) |

- **The 19 non-passing tests** all need `JEVDRILL_AGENT_HARNESS_ROOT` / `JEVDRILL_TEST_CLI`, which this session doesn't have (`tests/conformance/conftest.py:18-19`, `test_learning.py:297`, `test_usage_reporting.py:325`). This is the companion set the original fix record reran separately. Nothing else failed.
- **Generation and package checks also passed inside the full run:**
  - `test_generation_is_reproducible` passed.
  - `test_package.py` passed. It builds the wheel to a temp directory, checks the wheel contains `_boundary_schemas.json`, and runs the installed CLI outside the checkout.
- **Compiler skill check:** this session denied the command form that sets `BAML_AGENT_SKILL_CHECK=off`, so I couldn't set it myself. Parity passed in the launcher's environment, which `opus.launch.json` records as off. That is inferred, not observed.
- **Node fixtures:** parity passed for every row of every fixture file. I did not independently count the 197.
- **Not run (denied here):**
  - ruff/format and mypy, so the parent's lint/type results are unverified by me;
  - any ad-hoc Python probe;
  - native macOS/Windows runs.

## Prior items

| Item | Status | Evidence |
|---|---|---|
| D1: v2 label for new calls | Closed | `contracts.baml:154,164`; `jev.py:25`; guards at `application.py:749-754` and `jev.py:114-115`; `development.py:413`; driver `:1196` |
| D1: judge revision binding | Closed | `development.py:160-177` (binding at `:175`) |
| D1: validator binding | Closed | driver `:676-695` (`:691`); official-profile control and counterfactual at `test_discovery_calibration.py:546-582` |
| D1: route cache binding | Closed | `application.py:613-624`; `test_route_integration.py:370-421` |
| D1: replay compares request digest | Closed | `development.py:264-270`; `test_development_judge.py:199-212` |
| D1: docs line | Closed | `route-interfaces.md:86-97` |
| Fixture source binding | Closed | driver `:326-327`; `inputs()` reads the same `root` (`:107-110`, `:141-145`); drift control at `test_discovery_calibration.py:524-538` |
| Isolated optional-guidance test | Closed | see V2-3 |
| Shared field constant / `execution_token_limits` | Closed; O1 limits the test | `jev.py:27-56`; `application.py:764`; test `:210`, `:278-279` |
| `cheapest_feasible` reuse assertion | Closed | `test_discovery_calibration.py:507` |
| Timestamps in the projection | Closed: decision recorded | kept, and documented at `route-interfaces.md:91-93` |
| Generation status 4 | Closed | parity passes in this session |
| R1–R4 | Preserved | see V2-4 |
| F6/F7, D2–D6 | Unchanged, inherited | not re-argued |

## Acceptance criteria

**V2-1: met.**
- **Fails closed:**
  - The v2 check sits outside the inner fallback `try` (`application.py:749-754` against `:769` and `:803`). When judgment is needed, a v1 policy ends as `routing_failed` (`:868-874`) rather than silently falling back to a default. When judgment isn't needed, the policy is inert.
  - `:788` is the only dispatch site, and no other authored module builds a `JudgmentPolicy`.
- **New records are v2:**
  - `:794` rejects a v1 record coming back from a v2 dispatch.
  - The product adapter (`jev.py:114-115`, `:205`) and the dev judge (`:413`) both emit v2.
- **Historical v1 still parses:**
  - All seven schemas accept v1.
  - In Python and Node, v1 and v2 rows are accepted with pinned digests and v3 is rejected (`route-inputs.json:533-613`).
- **Stored replay is dispatch-free:**
  - Same-key route, `replay` and `load_replay` all return the unchanged v1 bundle with a judge that fails if called (`test_route_integration.py:306-367`).
  - `Application.replay` is a pure read of stored data (`:1277-1288`).
- **Recovery is verbatim:**
  - Recovery export/import parse the widened `RecoveryBundle` and store bundles unchanged (`storage.py:1167-1237`; `maintenance.py:441-451`).
  - No code re-checks `cache_digest`.

**V2-2: met.**
- **Product binding:** the function label, projection version, sorted field names and rendered-request digest (`jev.py:59-67`) go into the cache digest.
- **Development binding:** it adds the rendered task and discovery bodies (`jev.py:70-79`). These are exactly the bodies `_call` sends (`development.py:237-248`, `:284`), and the revision is checked on every receipt (driver `:917`, `:948`).
- **Controls:**
  - Same-binding reuse works, and a changed template, projection version or field set invalidates the cache (`test_route_integration.py:370-421`).
  - All five forms of profile drift are rejected without changing receipt or profile rows (`test_development_judge.py:148-196`).
  - A changed rendered body is denied without dispatch (`:199-212`).
- **No silent resume:** two guards do the work.
  - The grant preview binds `source_digest` (driver `:387`, `:415-421`), so the consumed grant can't validate against new source.
  - The study directory must be newly created (`:1009`).
  - The profile check (`development.py:186-188`) also protects any database that already has a profile row. I did not confirm that row exists in the Oct-9 database.

**V2-3: met, with O1.**
- **Fixture drift is caught:** adding a newline to either copied fixture after the run produces exactly the three source/exposure/authority errors.
- **The optional clause is now isolated:**
  - Required guidance is copied only from `request["active_guidance"]` (`application.py:1051`), so the optional mutation leaves it unchanged.
  - The honest `(3, None)` case pins no baseline error for case 3.
  - So the single pinned baseline error (`:470-478`) can only come from the optional-forbidden clause (driver `:845-848`). `:494-498` confirms the plan shape.
- **Field coverage:**
  - All 26 fields are emitted, now that the fixture fills `execution_token_limits`.
  - Unselected option IDs and text are absent (`:290-297`).
  - No pricing key is present in the frozen source.

**V2-4: met on Linux.**
- **Unchanged code:**
  - The R1 telemetry code (`development.py:343-360`) is unchanged.
  - The R2 allowlist has the same 26 names as the literal it replaced.
  - The R4 validator logic (driver `:845-862`) is unchanged.
- **Tests:** the tests for those three pass, and R3's false/true check (`test_route_integration.py:262-268`) passes.
- **Generation and package:** parity and the package build pass.
- **Schemas:** exactly seven schema files changed, out of 78 on disk and 78 in the manifest.
- **Driver scope:** the driver delta is limited to imports, two digest patterns, the expected-judge binding and the label constant. That means no collection, allowance, attribution, tolerance, paid-call, promotion, holdout or PREPARE change.

## Findings

**O1. Low: the field-set test can no longer catch a pricing leak (V2-3 "no private pricing"; R2's key-set pin).**
- **Trigger:** add `rates`, `cost`, `default`, `source`, `token_counter_revision` or `supported_efforts` to `JUDGMENT_CANDIDATE_FIELDS` (`jev.py:27-56`).
- **Consequence:**
  - The projection (`application.py:760-767`) would send that key to the provider.
  - `test_route_integration.py:278` would still pass, because both sides of its assertion are the same constant.
  - The value checks at `:290-297` catch unselected guidance IDs and text, not pricing keys.
  - No test pins the 26 names. The field list inside the binding digest (`jev.py:63`) would silently change cache and profile identities, but no test would fail.
- **The brief overstates the test:** "pins all 26 keys" is really "equals the constant, and every member is emitted."
- **Precedent:** this is the same shape as F3 and the round-2 optional gap: a guard can be weakened without a failing test. Nothing leaks today, and it doesn't affect D1 closure.
- **Minimal repair:** one test assertion, either:
  - `JUDGMENT_CANDIDATE_FIELDS.isdisjoint({"rates", "cost", "default", "source", "token_counter_revision", "supported_efforts", "guidance_options", "addresses_failures"})`, or
  - a literal 26-name set (or its digest) in the test.

**O2. Limited: verification still owed for an amended contract; not a delta defect.**
- **The rule:** `docs/contract-decisions.md:23` says every amended contract "adds positive/negative fixtures and repeats Python/Node parity and the OS matrix, including named validators."
- **Status by clause:**
  - Fixtures: done (`route-inputs.json:533-613`).
  - Python/Node parity: done (my runs).
  - OS matrix: not done. The parent states there is no new macOS/Windows evidence.
  - Named validators: I ran nothing beyond what the suite exercises.
- **Effect:** it doesn't bear on whether D1 or the carried blockers are closed in code. It gates relying on the amended contract at the freeze.
- **Repair:** run the configured macOS/Windows matrix for the seven schemas, or the president records an explicit deferral.

## Limitations and precision notes

- **Product binding vs. the body actually sent:**
  - **Hashed:** `IsSuitable@build_request` through the declared `Jev` client (`jev.py:65`; `jev.baml:1`, `:38-40`).
  - **Sent:** dispatch goes through `ObserveCandidate`, i.e. `typesafe_patch.internal.observe` (`jev.baml:21-28`; `jev.py:191-193`).
  - **Why they should match:** a test shows the patched and upstream clients send identical wire bodies (`test_jev_boundary.py:213-223`), and both use the same default model. No test compares `candidate_request_shape(t, c)` with a captured product request body, and my probes were denied.
  - **Contrast:** the development path is direct, since the hashed body is the sent body. Nothing shows divergence, so this is not a finding.
- **The product cache relies on manual versioning:**
  - It binds the template, field names and version, not the actual judged request bodies.
  - A change to how the task text is built (`application.py:770-782`) or how instructions are assembled (`:1051-1094`) would still reuse earlier cache entries unless someone bumps `JUDGMENT_PROJECTION_VERSION`.
  - The task-key pin at `:270-275` should prompt that bump. This is the binding the president specified.
- **What the mutation tests prove:**
  - The "fields" and "projection" mutations patch module globals that the binding reads, but `application.py` imports the constant at load (`:44-50`). So in those tests the real projection doesn't change.
  - They prove the binding invalidates, not that a projection change does. Production uses one shared object, so this isn't a defect.
- **The real historical record isn't tested:** no test parses the stopped study's actual v1 record (`evidence/EXPERIMENT/study-run-stop-diagnostic.json:106-118`). That it still parses rests on the literal widening, which is the only `JudgmentRecord` change, plus the synthetic v1 tests.
- **Injected judge returning v1:** a v1 record under a v2 policy is rejected by the existing check at `application.py:794` (the route falls back and the record isn't stored). No delta test exercises it.
- **Schema compatibility (an owner-approved observation, not a finding):**
  - **Backward compatible:** v1 payloads still validate, and digests are computed from payloads, so pinned v1 digests are unchanged.
  - **Forward-incompatible by design:** round-2 installs reject v2 policies and records, including recovery imports of bundles that contain v2 decisions.
  - The classification is recorded at `contract-decisions.md:31-33`, and no in-repo consumer breaks.
- **Doc nits:**
  - `route-interfaces.md:99` still says "nested unchanged v1 `route_inputs`."
  - The approved amendment sits under "Open questions" (`contract-decisions.md:25-36`).
- **No empirical or live activity:**
  - The loopback oracle answers 0.9 every time, so none of this is evidence of judgment quality.
  - No provider call, study, grant use, holdout access or credential read took place.

PARTIALLY AGREE
