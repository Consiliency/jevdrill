# President ruling — round 2 (final on R1–R4), three study-defect fixes

**Ruling: R1–R4 are closed and APPROVE_SCOPED_FIXES stands. The source freeze stays BLOCKED on D1, plus two small pre-freeze repairs that R4 itself made necessary.** No implementation is needed to close this round. A third round is required once the owner decides D1.

This is scoped code-review evidence only. It ratifies no empirical acceptance, grant, paid call, collection-policy change, merge or deployment.

"Driver" means `scripts/verify_discovery_calibration.py`.

## What I checked

- **Hashes:** all 11 manifest entries match the worktree at the start and end of my review, and the manifest digest is `13ffc320…6dfd`. The manifest has eleven entries, not twelve.
- **Delta:** the six changed files match `delta-binding.json`. `jev.baml`, the three generated-SDK files and `test_jev_boundary.py` have identical hashes in the round-1 and round-2 manifests.
- **Targeted tests:** I reran the five files myself: 97 passed.
- **Full suite:** I read the junit file directly. It shows 841 tests with 0 errors, failures or skips, and `test_generation_is_reproducible` passed in 2.025 s.
- **Generation parity:** it failed in my session too (status 4); see section 5.

**Limitations:**
- I could not hash the two `/tmp` receipts, so their recorded SHA-256 values are unverified by me.
- The junit start time (00:18:42) precedes the manifest's file time (00:21), and I could not read source mtimes. The full run's binding to the frozen bytes therefore rests on the parent's record plus the post-freeze reruns of the 97 (Astra, Grok, Opus, me).
- I did not run lint, mypy, the build, the full suite, or any probe. My session allowed only hashing and the two prescribed commands.
- No macOS or Windows evidence exists for this delta.

## 1. R1–R4

| Item | Ruling | Evidence |
|---|---|---|
| R1 | Closed | `development.py:350` emits `not_reported`, which is in the enum at `contracts.baml:2`. Six usage shapes, both record types, replay, two dispatches and `(2, 5506)` reservations at `test_development_judge.py:148-189`. Unknown cost still fails at driver `:452-453` and `:895-899`. |
| R2 | Closed | Allowlist at `application.py:745-780`; digest binding unchanged at `:804`. Key set, absence of unselected ID/revision/hash/role, four distinct combinations and populated-vs-cleared identity at `test_route_integration.py:272-322`. Reuse pinned at `test_discovery_calibration.py:482-484`. |
| R3 | Closed | Requirement satisfied in test data only (`test_route_integration.py:239`). False gives four exclusions of exactly `quality_unknown_or_insufficient`; true gives `ready` (`:256-262`). Production gate unchanged at `routing.py:145-149`. |
| R4 | Closed, with two carried pre-freeze items (section 3) | Task-required set at driver `:720-728` mirrors the merge at `application.py:971-992`. Conditions at `:838-855`; constructors at `:1296-1313`. Nine parametrizations with the error set pinned exactly (`test_discovery_calibration.py:453-461`). |

The rule matches the preregistered wording at `evidence/EXPERIMENT/study-proposal.json:59-62`.

## 2. D1 — still BLOCKED for source freeze

Both governing instructions are triggered, and they pull in opposite directions, which is why this is the owner's call.

- **Stop instruction:** `plans/detailed-pre-gepa-repairs-20261005-1336.md:87` says "Do not silently retain `JudgeCandidate-v1` if judgment semantics change: stop for an explicit versioned amendment on parity failure." `research/pre-gepa-review/reconciliation.md:31` accepts it as "Stop for a versioned amendment on a semantic change."
- **Freeze instruction:** `plans/phase-plan-v1-ROUTE.md:156-157` says "preserve JudgeCandidate-v1-only contracts."
- **Trigger:** the prompt changed (`jev.baml:4`), and R2 has now changed the judged payload a second time under the same label.
- **Label unchanged:** `contracts.baml:154,164`, `development.py:410`, driver `:1189`.
- **Nothing binds the template:**
  - The judge revision omits it (`development.py:159-175`).
  - The validator's expected value omits it (driver `:670-686`).
  - The route cache key omits it (`application.py:604-613`).
  - Replay compares only state and configuration digest (`development.py:260-266`), although a request digest is stored at `:246`.
- **Docs:** `docs/route-interfaces.md:75-79` still describes only the discovery payload.
- **Proposal status:** `proposed_owner_decision`. Neither elapsed time nor its "recommended" field is authorization.

**Owner choice required:**
- **Explicit v2 (still my recommendation).** New dispatches use `JudgeCandidate-v2`, v1 records stay readable, and the template digest plus projection version are bound in the three places above.
- **Recorded in-place v1 amendment** with the same bindings. The cost is that v1 then carries two meanings.
- **No decision.** The freeze stays blocked.

## 3. The three contested observations

**Two fixtures outside the source digest — introduced by R4; required before the next freeze.**
- **Introduced, not inherited:** in the correction base, `inputs()` was called only from `offline` and the study driver. R4 added the call inside `validate_study` (driver `:720`), so the validator's expected references now come from `tests/contracts/fixtures/discovery.json` and `route-application.json` (`:103-145`).
- **Not bound anywhere:** `source_digest` (`:313-330`) does not cover `tests/`. Both files are untracked in git and absent from the review manifest.
- **Immediate effect: none.** Both fixtures give an empty task-required set (`route-application.json:9`, `discovery.json:33`). By my reading, every R4 clause is additive to round 1's, so a fixture edit can only cause a false rejection. I did not execute that case.
- **Why it still matters:** a routine fixture edit after a paid study would fail validation with the baseline error and no "study source changed" signal. The D1 work is likely to edit these fixtures.
- **Repair:** add both paths to the digest patterns and add one control that mutates a copied fixture after the run. No test pins a literal digest (uses are dynamic at `:381`, `:698`, `:701`, `:1008`).
- **Current bytes, for the record:** `discovery.json` is `bd7ab28f593a0f0c315100bd79824f4a7253fd1b4eeb645f501ec99c761a155c`; `route-application.json` is `8c1c2a86054a526bc8040d0015c57df8c85f7a54f20d54e6b7e4a1dcc8d76af8`.

**Optional-guidance mutation conflates the required mismatch — test gap; required before the next freeze.**
- **The gap:** the "optional" case asserts the plan has no guidance at all (`test_discovery_calibration.py:477-480`), so its error comes from `required != retrieved` (driver `:850-851`).
- **Consequence:** deleting the optional clause at `:839-841` would leave all nine cases passing.
- **Why it now matters more:** R4 narrowed the retrieval check from required-plus-optional to required only. That clause is therefore the sole guard against an extra optional resource on `simple_retrieval`.
- **Code is correct by reading;** this is the same shape as round-1 F3, and I apply the same standard.
- **Repair shape:** extract the baseline predicate for per-clause tests, or forge a digest-consistent bundle with optional guidance on a baseline.

**Key-set test omits `execution_token_limits` — non-blocking for R2.**
- **Not a leak:** I agree with the parent. It is a limit consumed at `routing.py:116-122`.
- **The gap:** the allowlist has 26 keys (`application.py:765`) and the test pins 25. The study path sets the field (driver `:1208`), and only Grok's out-of-suite probe saw it.
- **When it becomes required:** it is part of the D1 amendment, which binds a projection version. Use one named constant shared by code and test, and a fixture row that populates every key.

## 4. Other Opus observations

- **`cheapest_feasible` reuse not asserted:** non-blocking. R2 required deterministic reuse to be shown, and two arms show it. Add the one-line assertion in round 3. Attribution (D2) is unchanged.
- **Timestamps in the judged payload:** non-blocking. Round 1 already sent `verified_at` and `expires_at`, so R2 retained them. They are stamped per candidate (driver `:1215`) before baselines are copied (`:1279`), so pairing within a case holds. Decide whether they belong in the projection before D1 binds it.
- **F6/F7 and D3–D6:** unchanged and inherited.

## 5. Generation parity

- **Reproduced:** the version gate passes, then `generate` at `check_generated_contracts.py:130` exits with status 4. The whole test fails in 0.14 s.
- **Correlation:** every failing attempt, mine and the four in the Opus stream, wrote to `/mnt/workspace/users/viperjuice/tmp/…`. Both failing sessions are the manual Claude CLI route.
- **Undiagnosed:** the script captures stderr, and my session denied a rerun with `TMPDIR=/tmp`. The temp directory is a lead, not a cause.
- **Why parity still stands for round 2:** there are three passing receipts from other environments (parent junit, Astra, Grok), no delta file is a generation input, and the generation hashes are unchanged.
- **Before round 3:** this must be diagnosed, because D1 regenerates the SDK.

## 6. Next blockers and round 3

1. **Owner decides D1.** Nothing else unblocks the freeze.
2. **One round-3 delta** (the last under the cap) carries:
   - the D1 amendment with its three bindings;
   - regenerated SDK and schemas;
   - the docs line;
   - the shared projection constant;
   - the fixture digest binding;
   - the isolated optional-clause test.
3. **Round-3 manifest** must add both fixtures, `contracts.baml`, `boundary.json` and the regenerated outputs.
4. **Parent diagnoses status 4** in a Claude CLI shell with stderr visible, so the Opus seat and president can verify the new SDK.

A third review is required if the owner approves either amendment form: Astra, Opus and Grok delta reviews, then a president ruling. If the owner declines, the freeze stays blocked. The two carried repairs would still need a small reviewed delta before any freeze.

No further rereviews are needed for this round.

**APPROVE_SCOPED_FIXES: yes, for R1–R4.**
**Source freeze: BLOCKED — D1 owner decision pending; fixture digest binding and the optional-clause test are also required before the freeze.**

PARTIALLY AGREE
