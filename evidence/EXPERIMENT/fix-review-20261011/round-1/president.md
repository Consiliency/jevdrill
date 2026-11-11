# President ruling — round 1, three study-defect fixes

**Ruling: APPROVE_SCOPED_FIXES.** Three defects and one test gap are upheld and must be repaired. One owner decision (the `JudgeCandidate-v1` label) stands as a blocker on the next source freeze. A new final ruling is required after round 2.

**What I checked.** All 11 manifest hashes matched at the start and end of my review. I read every cited location and reran the 84 targeted tests (all pass). I did not run generation parity or ad-hoc probes, because this session permitted only tests and hashing. Astra's loopback reproduction of F1 is therefore accepted on static confirmation of each step.

`correction-base/` is byte-identical to the round-1 source, so no pre-fix copy of the untracked files exists. "Inherited vs introduced" rests on the original defect review's description.

"Driver" below means `scripts/verify_discovery_calibration.py`.

## 1. Findings

| # | Finding (seat) | Ruling | Criterion |
|---|---|---|---|
| F1 | Missing input usage poisons the receipt (Astra) | **Upheld, blocker, medium** | FIX-1, FIX-4 |
| F2 | Suitability payload is the whole internal row (Opus B2, Grok) | **Upheld, blocker, medium** | FIX-2 |
| F3 | False-judgment test does not discriminate (Astra) | **Upheld, required test fix** | FIX-2 |
| F4 | Validator ignores required guidance on non-retrieval arms (Grok, Opus) | **Upheld, limited; repair restated** | FIX-3 |
| F5 | Semantics changed under the `JudgeCandidate-v1` label (Opus B1) | **Upheld; owner decision** | FIX-4 |
| F6 | No cost re-derivation for `cheapest_feasible` (Grok) | **Rejected as patch blocker; inherited** | — |
| F7 | Duplicate call IDs or metric rows are summed (Grok) | **Rejected as blocker; inherited hardening** | — |
| F8 | 8,192-byte cap fires mid-loop (Opus) | **Limited; no trigger shown** | — |
| F9 | Gemini AGREE, no blockers | **Rejected as a basis for approval** | — |

**F1.**
- **Trigger:** `development.py:350` emits `input_tokens_not_reported`, which is not in the enum at `contracts.baml:2`.
- **Mechanism:** the receipt is stored as completed at `:359-368` before `parse_contract` rejects it at `:405-417`. Replay at `:260-266` returns the same poisoned measurements.
- **Reach:** discovery judgments fail identically (`:377-393`), since both share `_call`.
- **Local rule broken:** `plans/detailed-pre-gepa-repairs-20261005-1336.md:85` prescribes `not_reported` for absent counters.
- **Status:** inherited line, but FIX-1's "unknown counters remain unknown" cannot hold with it.

**F2.**
- **Trigger:** `application.py:1017` copies the candidate including `guidance_options`; `:745-748` drops only `cost`.
- **Test blind spot:** the check at `test_route_integration.py:271` cannot see this, because "unoffered" was never an option (`:205`, `:235`).
- **Consequence:** the actual arm populates options (driver `:1223-1234`) and baselines clear them (`:1291-1292`). The same unguided configuration therefore gets two receipt identities (`development.py:242`), is charged twice, and can receive contradictory verdicts.
- **Severity:** that perturbs the paired comparison, so Grok's "high" is reduced and Opus's "low" is raised.

**F3.** The test adds a requirement at `:234`; the fixture has `satisfied_requirements: []` (`route-application.json:100`). `routing.py:147-149` therefore excludes every candidate regardless of the Boolean, and `:251` passes either way.

**F4.**
- **Gap confirmed:** `required_guidance` is unchecked for the three non-retrieval arms (driver `:824-826`).
- **Why the proposed repair is wrong:** "require applied guidance empty" misstates the preregistered conditions. `study-proposal.json:59-61` defines these arms as "task-required guidance only" and "optional guidance removed".
- **Why it happens to coincide:** the frozen task-required set is empty (`route-application.json:9`, `discovery.json:33`), so empty is the correct evaluation here but not the correct rule.

**F5.**
- **Changes:** the prompt changed (`jev.baml:4` against HEAD) and so did the payload (`application.py:751-763`, `:1075`).
- **Label unchanged:** `contracts.baml:154,164`, `development.py:410`, driver `:1172`.
- **Instruction:** `plans/detailed-pre-gepa-repairs-20261005-1336.md:87`, accepted at `research/pre-gepa-review/reconciliation.md:31`: "Stop for a versioned amendment on a semantic change." The fix record documents no label decision, so this is silent retention.
- **Scope:** the change also reaches the product path (`jev.py:131-133`), not only the development judge.
- **Missing bindings:** the route cache key (`application.py:604-618`), the judge revision (`development.py:159-175`) and the validator's expected value (driver `:670-686`) do not bind the prompt.
- **Mitigation:** the study source digest covers `baml_src` (driver `:313-330`), which is why this blocks the freeze rather than the repairs.

**F6, F7.**
- **Honest runs:** the driver emits unique sorted IDs (`:1253-1258`, `:1299-1302`) and one row per metric (`contracts.py:266-299`), so they are unaffected.
- **F7 predates the fix:** the cost path already summed over the same list (driver `:791-794`).
- **F6 would duplicate routing:** re-deriving the cheapest model would reimplement routing feasibility in the validator.

**F8.** Opus's static estimate is about 4.8 KB against the cap; nobody ran it. F2's repair shrinks the payload further.

**F9.** Gemini reviewed excerpts with no tools. Its statement that baseline preconditions are "enforced" is contradicted by driver `:824-835`, and it missed F1 and F2.

## 2. Corrections

**Required (round 2):**

- **R1 (F1):**
  - **Code:** emit `not_reported`.
  - **Tests:** loopback cases for absent usage, `{}`, null input with known output, and both null.
  - **Coverage:** task and discovery records, plus replay with no second dispatch.
  - **Constraint:** unknown cost must still fail study validation (driver `:878-882`).
- **R2 (F2):**
  - **Code:** judge an explicit allowlisted projection.
  - **Tests:** pin the key set; assert no unselected option's ID, revision, hash or role appears.
  - **Identity test:** the same configuration serializes identically with options populated or cleared.
  - **Constraints:** the four combinations stay distinct; no prompt change.
- **R3 (F3):**
  - **Fix:** mark the synthetic requirement satisfied in the test's own data. This is test data, not a production prior.
  - **Assert:** all-false gives `no_compatible_plan` with `quality_unknown_or_insufficient`, and a true counterfactual becomes ready.
- **R4 (F4):**
  - **All four baselines:** optional guidance empty.
  - **Non-retrieval arms:** required guidance equals the task-required set.
  - **`simple_retrieval`:** required guidance equals the retrieved list.
  - **Wording:** code and error text must state the preregistered condition.
  - **Retained mutation tests:** substituted and extra resources on `simple_retrieval`, and injected required guidance on a non-retrieval arm.

**Authorized but optional (tightening only):** a duplicate-ID and one-row-per-metric guard (F7), and an offline all-cases request-size test (F8).

**Owner decisions, not authorized here:**

- **D1 (F5):**
  - **Why the owner must decide:** a v2 bump changes a `const` in seven public schemas, which FIX-4 says to preserve; retaining v1 silently is what the plan forbids.
  - **Recommended: explicit v2.** New dispatches emit and require `JudgeCandidate-v2`. Records accept v1 or v2, so stored bundles and the 14 stopped-study receipts still parse and replay.
  - **Binding:** a request-template digest goes into the judge revision, the validator and the route cache key.
  - **Sequencing:** land it with or after R2 so the payload is bound once.
  - **Alternative:** a recorded in-place amendment of v1 with the same digest binding. I do not recommend it, because v1 records would then carry two meanings.
  - **Docs:** add one line to `docs/route-interfaces.md` that instruction bodies of offered combinations now reach the judgment provider.
- **D2:** R2 makes receipt reuse across arms more frequent, so per-arm navigation cost becomes more order-dependent. Attribution policy stays unchanged in this patch; R2's test must show the reuse deterministically.
- **D3:** `cheapest_feasible` re-derivation (F6).
- **D4:** abstention stopping collection. `simple_retrieval` now has no unguided fallback (driver `:1303-1304`).
- **D5:** route judgments ignore `allowed_providers` (`application.py:731-737` vs `:153-157`).
- **D6:** `offline()` alignment and two-resource coverage, which needs a protocol change.

Ask the owner for D1 now, in parallel with round 2. If it lands in round 3 there is no slack under the cap.

## 3. Delta rereview seats

- **Astra — required.** R1 and R3, plus a rerun of the targeted suite and generation parity.
- **Opus — required.** R2, R4, and D1 if it lands. Give this seat `BAML_CLI`.
- **Grok — required.** R2 and R4. It must run the tests this time, or its delta counts as source-read only.
- **Gemini — not required.** It has no open finding and cannot verify.

The round-2 manifest must show the three generated-SDK hashes unchanged unless D1 lands. All three required seats finish before any further fixes.

## 4. Verdict

No empirical acceptance, grant, paid call or collection-policy change is ratified or implied. Historical evidence stays untouched.

APPROVE_SCOPED_FIXES

PARTIALLY AGREE
