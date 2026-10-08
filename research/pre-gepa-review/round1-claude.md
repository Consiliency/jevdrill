**Verdict: PARTIALLY AGREE**

The direction is sound. BAML stays, GEPA is deferred, work starts offline, unknowns stay unknown, nothing is promoted, and the stop conditions are evidence-based. But nine in-scope blockers leave AC3, AC6 and AC7, and the WP-C design, either unprovable or likely to fail as written. Each has a small repair. I made no edits and ran nothing.

## Blockers

1. **WP-B's stop condition is already met, so AC3 can't pass as written.** (AC3; plan lines 63–67)
   - **Evidence:** a null output counter already fails with `BamlError` after one request, and nothing is retained (`usage-diagnostics.json:54-68`). Both pinned usage types require non-null `output_tokens: int` (`src/baml_sdk/vendor/typesafeai/internal/__init__.pyi:106-108`, `src/baml_sdk/ai/events/__init__.pyi:106-110`). A direct `cl.invoke` uses the same `typesafeai.internal.invoke`. So package B stops even if numeric `ModelTurn.usage` turns out to be intact.
   - **Repair:** split AC3 in two.
     - (a) Numeric, zero and absent-usage capture through one direct turn must pass, or package B stops with a reproduction.
     - (b) Null or omitted counters must fail closed: a redacted typed failure, exactly one loopback request, no projected counters, and the reservation kept. Record this as a pinned-bridge limitation, not a package stop.
     - Add omitted-key fixtures (`{"input_tokens":123}`, `{}`) to show the bridge doesn't default missing counters to zero.
     - If the owner does want a stop, say plainly that WP-B is expected to stop.

2. **The product's measurement path is skipped when the adapter is injected.** (AC3 "survives"; plan line 57)
   - **Evidence:** `observe` → `details.measurements` (`application.py:340-360`) is only wired when the application builds the adapter itself (`application.py:267`). The historical harness injects its own adapter (`study.py:109`) and computed routing cost from its own callback (`study.py:121-123`). The adapter always returns `measurements: []` (`jev.py:105`).
   - **Consequence:** if WP-C reuses that harness, the WP-B change in `application.py` never runs.
   - **Repair:** carry per-call observations in the already-public `JudgmentRecord.measurements` (`contracts.baml:219-221`) and project them once from the validated record, whether or not the adapter is injected. Say which field is authoritative for aggregation. Add an injected-adapter loopback test to `test_route_integration.py`.

3. **The usage precedence rule contradicts itself.** (AC3 "conflicts"; plan line 56)
   - **Evidence:** "Turn usage is authoritative when present" and "conflicting counters become unknown" give different answers for turn=10 vs event=12. There's no rule for turns with several calls (`ModelTurn.calls`), where the turn total should equal the sum of the calls. `MissingReason` has no conflict value (`contracts.baml:2`).
   - **Repair:** write a per-counter decision table and pick one rule for conflicts, using an existing reason or diagnostic. Compare multi-call turns against the sum of their calls. Test with synthetic objects, since one loopback response can't produce conflicting surfaces.

4. **AC7's audit contradicts the planned edits.** (AC7)
   - **Evidence:** the historical study pins `application.py`, `jev.py`, `telemetry.py`, `jev.baml` and `_inlinedbaml.py` (`verification.json:36-77`). Its runner re-hashes all of `src/jevdrill` and `baml_src` (`study.py:157-162`) and checks them before dispatch (`study.py:244`). `application.py` and `_inlinedbaml.py` are uncommitted.
   - **Consequence:** WP-B edits or regenerates these files, so the start/end audit either fails or proves nothing, and the bound pre-change bytes are lost.
   - **Repair:** before any edit, snapshot all bound paths and verify them against `verification.json`. Define the end audit as a list of allowed changes plus "everything else unchanged". Run any historical replay against the snapshot.

5. **"Two candidates per route" isn't guaranteed.** (plan lines 75, 84)
   - **Evidence:** each model expands into 1+n+C(n,2) guidance rows (`application.py:426-434`), and routing keeps only the first `max_candidates` rows in candidate-ID order (`application.py:244-262`).
   - **Consequence:** with any optional guidance, both judged rows can be Groq variants. Luna is then never judged and is excluded (`routing.py:142-143`).
   - **Also:** `bounded_candidates` (`jev.py:25-38`) silently drops the second model when the longer task text exceeds the 30,000-byte bound.
   - **Repair:** state how guidance is delivered (required `active_guidance` or in the task text). Add an offline check that every calibration case judges exactly one row per offered model under the frozen policy.

6. **Reused cached decisions copy per-call usage.** (plan line 57, "once per call")
   - **Evidence:** `application.py:167-180` deep-copies `details.measurements` (scope `call`) into a new decision without making a new call.
   - **Consequence:** harmless today because the counters are unknown, but it double counts once WP-B works.
   - **Repair:** drop call-scope routing measurements on reuse, and add a test for it.

7. **Nothing proves the new helper judges the same way while `function_revision` stays `JudgeCandidate-v1`.** (AC4; `contracts.baml:210,220`)
   - **Evidence:** JEV returns scores that are decoded to a Boolean (`noul: 0.9` → `True`, `test_jev_boundary.py:21`). `.call()` may go through an Agent repair loop (`schema_attempts=2`, `ai/__init__.pyi:115,176-185`).
   - **Repair:** add loopback parity fixtures:
     - byte-equal request bodies on the old and new paths;
     - the same Booleans at score boundaries (0 / 0.49 / 0.5 / 0.51 / 1) and for malformed answers;
     - exactly one request per candidate in every fixture.

     Stop if parity fails.

8. **AC6 claims offline-proven replay diagnostics, but no listed test covers them.** (plan line 76 vs line 86)
   - **Repair:** add a test that changes an evidence file, rewrites the SQLite file physically without changing its data (e.g. VACUUM), and changes a row. Against an immutable snapshot, assert that the path, before/after hashes, and physical-vs-logical classification are recorded. Open replay databases read-only.

9. **No analysis can show the stated aim of beating "always admit".** (plan lines 5, 88; AC6 "frozen criteria")
   - **Evidence:** rejection rates and selection variation don't measure usefulness. "Always admit" is simply fixed Groq for cost and fixed Cerebras for speed. Historical failure rates (4/60 and 2/60) predict only about 1–3 cheap-model failures in 36 cases.
   - **Repair:** pre-register, before any calls:
     - a per-candidate 2×2 of JEV's judgment against that model's paired fixed-arm outcome;
     - a minimum failure count below which the result is "insensitive".

     Or restate the aim as a descriptive baseline.

## Recommendations (non-blocking)

- Run the WP-B checkpoint against a private SDK under `.phase-loop/runs/PRE-GEPA-20261005/`, so product BAML isn't regenerated before the decision. Add the missing branch: if both surfaces carry counters, fix `telemetry.py` instead.
- Define "usable usage" (plan line 82) and how routing cost is valued. Historical runs used uncached list rates with `cached_input_tokens: null` (`results.json:982-996`). `estimate_usage_cost` returns unknown whenever any counter is `None` (`costing.py:84`), and JEV's usage type has no cached field.
- Record explicit unknown measurements for calls that were sent but failed, including `routing_failed` outcomes. Today they're dropped (`application.py:364-370`).
- **WP-A:**
  - Name one authored schema source; the plan names both the dataset schema and BAML.
  - Grade the strictly parsed raw value.
  - Define the accepted envelope, including whether code fences are allowed. Historical outputs had none.
  - List duplicate-key, NaN and `1.0`/`true`/`"1"` integer fixtures.
- **AC1:** cover all 20 groups / 60 cases, not just the "corrected" ones.
- **AC4:** bind it to the real timeout and cancellation tests, and run cancellation through the new helper. The current async test uses the old path.
- Add `scripts/check_import_boundaries.py` to Verification. `integrations` can't import `telemetry` (`vocabulary.yaml:279,286`).
- **AC5:**
  - `docs/route-interfaces.md` is outside the lint scope (`vocabulary.yaml:292`).
  - `resource`, `task` and `measurement` aren't registry concepts.
  - Avoid adding "executive harness" and "resource selection" as quasi-terms.
- Say whether the dispatch record is per routing attempt (covering up to 2 JEV calls) or per JEV request.
- Pre-register the arm stop rule. The old runner stops a whole arm on the first `routing_failed` (`study.py:276-279`). Also compute the worst-case reservation before admission.
- Don't let the offline verifier overwrite a different existing `offline.json`.
- Optionally keep raw JEV scores in private evidence (not as a threshold), so later calibration has something to work with.

**Not verified:** the reservation logic in `base.attempt`, and the plan's claim that BAML turned nested arrays into strings. My quick searches of `results.json` didn't find it, but my patterns may have missed it.

## Files read

- **Plan and evidence:**
  - `research/pre-gepa-review/brief.md`
  - `plans/detailed-pre-gepa-repairs-20261005-1336.md`
  - `research/pre-gepa-review/plan-round1.md` (headings only)
  - `evidence/EXPERIMENT/routing-comparison-20261005/{summary.md, usage-diagnostics.json, protocol.json, verification.json}`
  - `results.json` (lines 975–1014 plus searches)
  - `evidence/ROADMAP/latest-study.json`
  - `provider-typed-proof-20261004/summary.md` (excerpt)
- **Code and BAML:**
  - `baml_src/jev.baml`
  - `contracts.baml` and `boundary.json` (excerpts)
  - `development.baml`, `pilot.baml`, `review_pilot.baml` (excerpts)
  - `src/jevdrill/{application.py, telemetry.py, integrations/jev.py}`
  - `costing.py`, `contracts.py`, `routing.py`, `cli.py` (excerpts)
  - `src/baml_sdk/ai/__init__.pyi`
  - `ai/events/__init__.py(i)`
  - `vendor/typesafeai/__init__.pyi` and `internal/__init__.pyi`
  - `_typemap.py`, `__init__.pyi` and `.gitignore` (excerpts)
  - `baml_bridge/proto.py` (search only)
- **Tests:** `tests/contracts/test_jev_boundary.py`, `tests/integrations/test_jev.py`, `tests/privacy/test_jev_privacy.py`, `tests/application/test_route_integration.py`
- **Scripts:** `scripts/check_generated_contracts.py`, `scripts/lint_vocabulary.py`
- **Docs:** `docs/contracts.md`, `docs/route-interfaces.md`, `docs/vocabulary.yaml`, `docs/jevdrill-spec.md:180-201`
- **Historical run:** `.phase-loop/runs/ROUTING-comparison-20261005/study.py`, `baml_src/proof.baml`
