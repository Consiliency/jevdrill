# President ruling, round 3 (final under the cap): JudgeCandidate‑v2 amendment and carried repairs

**Ruling: APPROVE_SCOPED_FIXES.** The final source `4fb3ed65…fd6b` is ready for the bounded code fix.
- **Closed:** D1, the fixture‑source binding, the isolated optional‑guidance test, and Opus's O1 and O2.
- **Preserved:** R1–R4.
- **No blocker remains.** No round 4 is needed.

This is a scoped manual implementation‑review ruling only. It is not governed phase acceptance or a governed freeze, and it ratifies no empirical counts, tolerances or quality. It grants no study, grant reuse, collection, merge, deployment or publishing authority. It does not rest on a clean, formally completed three‑seat panel; see section 7.

"Driver" means `scripts/verify_discovery_calibration.py`.

## 1. What I checked

**Hashes**
- **Manifest checks before and after:** `sha256sum --quiet -c` passed for `final-source-manifest.sha256` (243 source files) and `base-manifest.sha256` (243 preserved correction‑base files). Both passed before my first check and after my last.
- **Manifest digests:** final `4fb3ed65…fd6b`, original reviewed `d6277cc6…eab8` (retained unchanged), base `9cf16b00…a656`.
- **Review head to final:** exactly one path differs, `tests/application/test_route_integration.py` (`4abf0153…` → `5eea3d05…`).
  - A `diff -u` from the preserved round‑2 copy to the current file equals that file's `delta.diff` hunks plus the 12 lines of `supplement.diff`, and nothing else.
- **Base to review head:** exactly the 27 paths in `delta-binding.json`, including exactly seven schemas.
  - Both validator fixtures are unchanged and equal the round‑2 recorded bytes (`bd7ab28f…`, `8c1c2a86…`).
- **Historical files:** I re‑hashed 13 files and all match the parent's pre‑edit baseline (`/tmp/jevdrill-inline-before.json`). They include the stopped‑study `judgments.db` (`be59fa07…`), the study, exposure, lineage, controller and worker artifacts, `study-proposal.json`, `study-authorization.json`, `study-run-stop-diagnostic.json` and the suitability review.
- **Timeline (file modification times):**
  - Astra's review 11:23:00; Opus's review 11:43:02.
  - Grok's delivery record, already `cancelled`, 13:58:35.
  - Test file edit 13:58:43.
  - Final manifest and binding 13:59:04; the parent's guard junit 13:59:15.

**Commands I ran on the final source** (pytest with `-p no:cacheprovider`)

| Check | Result |
|---|---|
| The two affected controls, `test_suitability_receives_exact_offered_guidance_and_authorized_task_context[False/True]` | 2 passed |
| The six focused files named in the brief | 130 passed (45.4 s) |
| Pinned generation parity (`BAML_CLI` 0.20.1) | `{"passed": true, "generated_files": 147, "schemas": 78, "write": false}` |
| `tests/contracts tests/evaluation` (the native‑matrix test set; includes Python and Node parity over every `route-inputs.json` row) | 322 passed, 0 skipped |

**Receipts I read directly:**
- `/tmp/jevdrill-v2-full.xml`: 858 tests, 0 errors, 0 failures, 0 skips.
- The final guard junit: 2 tests, 0 failures.
- All three native receipts and the native logs.

**Denied in this session.** These are tool limits, not defects:
- pytest prefixed with `BAML_AGENT_SKILL_CHECK=off` (the launcher records it as already off);
- ruff check and format;
- a read‑only Python recompute of `input_digest`/`reduce_manifests`;
- hashing or listing the native snapshot outside the worktree;
- comparing `git diff --cached` with the index baseline.

I ran no git commands. My only writes were junit files in `/tmp`.

## 2. Prior blockers and carried items

| Item | Ruling | Evidence |
|---|---|---|
| D1: new calls use v2; v1 cannot dispatch | **Closed** | See "D1 dispatch guard" below the table. |
| D1: historical v1 parse and replay | **Closed** | The seven schemas change only `const v1` to `anyOf[v1, v2]`. `route-inputs.json:521-609` accepts v1 and v2 with pinned digests and rejects v3, in both Python and Node. See "D1 historical replay test" below the table. |
| D1: template and projection bindings | **Closed** | See "D1 bindings" below the table. |
| D1: no silent resume | **Closed** | The study directory is created with `exist_ok=False` (driver `:1009`). The grant preview binds `source_digest` (`:387`, `:415-425`). Any database with an existing profile row is refused (`development.py:186-189`). |
| D1: docs | **Closed** | `docs/route-interfaces.md:86-97`, `docs/contract-decisions.md:27-36`, `plans/phase-plan-v1-ROUTE.md:157-160`. |
| Fixture‑source binding | **Closed** | Both fixtures are added to the digest at driver `:326-327`. `inputs()` reads them from the same `root` (`:109`, `:142`) that `source_digest(root)` hashes (`:705`, `:708`). See "Fixture drift control" below the table. |
| Isolated optional‑guidance test | **Closed** | See the reasoning after the table. |
| Shared field constant and `execution_token_limits` | **Closed** | `jev.py:27-56` holds the same 26 names as the literal it replaced; the filter is at `application.py:760-767`. The fixture fills the field (`test_route_integration.py:206-211`). Every judged row equals the constant and carries the limits (`:289-291`). |
| `cheapest_feasible` reuse | **Closed** | `test_discovery_calibration.py:507`. |
| Timestamps in the projection | **Closed; decision recorded** | Kept deliberately (`docs/route-interfaces.md:91-93`). |
| Generation status 4 | **Closed** | Parity passes in this session. |
| R1 | **Preserved** | `development.py:343-360` is unchanged; unknown cost stays `not_reported` (`:353`). |
| R2 | **Preserved** | Same allowlist. Unselected IDs, revisions, hashes and roles are absent, and the four instruction tuples are distinct (`test_route_integration.py:301-310`). The payload is identical with options populated or cleared (`:311-315`). |
| R3 | **Preserved** | `test_route_integration.py:262-268`. |
| R4 | **Preserved** | The baseline predicate (driver `:845-862`) is not in the delta. Nine parametrizations (`test_discovery_calibration.py:288-301`) pin the error set exactly (`:469-478`). |

**D1 dispatch guard**
- The live label constant is at `src/jevdrill/integrations/jev.py:25`. The schema literal is at `baml_src/contracts.baml:154,164`.
- The route guard (`src/jevdrill/application.py:751-754`) runs before judge selection (`:768`), so it also covers injected judges.
- The guard sits outside the inner `try` (`:769`). A v1 policy therefore ends as `routing_failed` (`:868-874`) with no fallback.
- The adapter has its own guard (`jev.py:114-115`).
- `application.py:788` is the only dispatch site, and `JudgeCandidate(` appears only at `jev.py:191`.
- The driver injects `DevelopmentJudge` through `Application` (driver `:1034-1049`) and takes the label from the constant (`:1196`).
- Records emit v2 (`jev.py:205`, `development.py:413`). A record with a mismatched label is rejected at `application.py:794`.

**D1 historical replay test** (`test_route_integration.py:318-379`)
- Builds v1 ReplayBundle, RecoveryDecision and RecoveryBundle payloads, and all three parse unchanged.
- A same‑key route, `replay` and `load_replay` all return the stored v1 bundle unchanged. The injected judge raises `AssertionError` if called.
- A new idempotency key with a v1 policy returns `routing_failed`.
- The test discriminates: without the guard, the `AssertionError` would escape `route`.
- Same‑key retry returns at `application.py:570-609`, before any binding is computed.

**D1 bindings**
- `jev.py:59-67` digests the label, projection version, sorted field names, and the rendered `IsSuitable@build_request` body. It hashes the body only, with no key or URL (`baml_src/jev.baml:38-40`), so it is the same across processes and environments.
- `jev.py:70-79` adds the rendered development task and discovery bodies.
- The bindings reach:
  - the product cache digest (`application.py:613-624`);
  - the development judge revision (`development.py:160-177`), with refusal of a changed profile at `:186-189`;
  - the validator's expected value (driver `:676-695`);
  - the per‑receipt request‑digest check (`development.py:264-270`).
- Tests:
  - `test_route_integration.py:382-433`: same‑binding reuse, plus invalidation on template, projection and field changes.
  - `test_development_judge.py:149-196`: five profile drifts rejected without touching receipts.
  - `test_development_judge.py:199-212`: a changed rendered body is denied without dispatch.
  - `test_discovery_calibration.py:546-582`: the official profile matches the validator, and a changed template does not.
  - `tests/integrations/test_jev.py:38-40`: the adapter rejects a v1 policy directly.

**Fixture drift control** (`test_discovery_calibration.py:524-538`)
- Appending a newline to either copied fixture after the run adds exactly three diagnostics: study source changed, exposure/source/grant mismatch, and authority differs from preview.
- Restoring the bytes restores the original error set.
- A newline leaves the parsed content unchanged, so this tests drift detection rather than semantics.

**Why the optional‑guidance error is now isolated**
1. The fault (`test_discovery_calibration.py:412-422`) leaves `active_guidance` untouched and adds one extra optional reference.
2. The `_prepare` filter (`:439-448`) forces an optional profile only on `simple_retrieval`.
3. The executed plan is pinned (`:494-498`): required guidance is the prescribed retrieval list, and optional guidance is the extra resource.
4. Required guidance is copied only from `active_guidance` (`application.py:1051`), and the validator ignores only `token_count` (driver `:841-844`). The required references therefore equal those of the honest `(3, None)` case, which produces no baseline error.
5. Because the error set is pinned exactly, the single baseline error can only come from the optional‑forbidden clause (driver `:846-848`). Deleting that clause would now fail this case.

Astra removed the clause in memory and the error disappeared. I could not repeat that probe (no source edits allowed; ad‑hoc Python denied).

## 3. O1 and O2

**O1: closed by the supplement** (`test_route_integration.py:277-288`)
- **Independent and exact:** the forbidden set is a literal written in the test, not derived from the implementation. It is exactly the minimal repair Opus proposed.
- **Complete against the real row:**
  - Every `CandidateSnapshot` field outside the shared constant is in the forbidden set: `supported_efforts`, `source`, `token_counter_revision`, `rates`, `default`, `guidance_options`, `addresses_failures` (`baml_src/contracts.baml:117-127`).
  - So is `cost`, which `_prepare` adds (`application.py:1096`).
  - The other row‑only keys are `exclusion_reasons`, `predecessor_plan_id`, and `fallback_used` (added only after judgment). None is pricing or menu data, and the equality check at `:290` keeps them out of the judged row.
  - Adding any named pricing or menu key to the constant now fails the test.
- **Residual (suggestion only; no criterion is violated):** the 26 names are not pinned literally. Removing a field, or adding a new private field to both the schema and the constant, would pass this test. Either change would still alter `candidate_fields` in the binding digest, which invalidates the cache, profile and validator identities.

**O2: closed**
- **The rule:** `docs/contract-decisions.md:23` requires fixtures, Python/Node parity, and the OS matrix with named validators.
  - Fixtures: done (`route-inputs.json:521-609`).
  - Python/Node parity: done (my 322‑test run and all three receipts).
  - OS matrix: done (the native receipts below).
- **Native receipts:**
  - Linux x86_64 3.13.15, Darwin arm64 3.13.7 and Windows AMD64 3.13.15.
  - All have `execution_kind: native`, compiler and bridge 0.20.1, and the same input digest `1aa52756…`.
  - Each ran 322 tests with 0 skipped.
  - Every named check exits 0: tests, generation, coverage, vocabulary, glossary, imports, lint, format, types and build. Linux also runs `catalog`.
  - I checked each receipt against every rule in `scripts/verify_contract_phase.py:39-63` by reading it; none violates a rule.
  - Windows ran native `…\Scripts\python.exe` and reports `os: Windows`; Python under WSL would report Linux.
- **Setup corrections were not product changes:**
  - The first native Linux attempt failed four Node‑consumer tests and `catalog`; the log shows `research/evaluation/cases.json` was missing from the snapshot.
  - That failed run reports the same input digest. So the corrections touched only files outside the digest, meaning setup rather than product code.
  - The native logs show no sign that TLS verification was disabled.
- **Precision limits:**
  - The native `tests` check runs only `tests/contracts` and `tests/evaluation`. The final test file is covered natively only through `input_digest` (which includes `tests/**/*.py`, `verify_contract_phase.py:23-36`), not by being executed. The O1 assertion has run on Linux only.
  - Native lint and format cover `src`, `tests/contracts` and `tests/evaluation`, not `tests/application`.
  - That the final worktree's digest equals `1aa52756…` is the parent's record (`final-binding.json`), and I could not recompute it. Three things corroborate it:
    - the final manifest verifies;
    - the snapshot's copy of the changed region and its length match on visual inspection;
    - my local run of the same test set gave 322 passed, 0 skipped.
- No deferral is needed.

## 4. Final test delta and readiness

- **The delta:** one 12‑line assertion inside one test.
  - No new imports.
  - The manifests show no production, schema, SDK or generated‑file change.
  - It catches O1's trigger.
- **Execution:** the assertion runs under both parametrizations, and both pass on the final source (the parent's run and mine). The 130 focused tests and generation parity also pass.
- **Final‑source readiness for the bounded code fix: READY.** Every pre‑freeze condition from the round‑2 ruling is met:
  - D1 decided and implemented, with regenerated SDK and schemas;
  - the docs line;
  - the shared field constant;
  - the fixture binding;
  - the isolated optional test;
  - a manifest that includes both fixtures, `contracts.baml`, `boundary.json` and the regenerated outputs;
  - the status‑4 diagnosis.

## 5. Procedural ruling: the supplement within the cap

The test‑only supplement is accepted as closing round 3, without a round 4.
- **Timing:** it was applied after every seat reached a terminal state (13:58:43, against Grok's `cancelled` record at 13:58:35). Grok's own after‑hashes still matched `d6277cc6`.
- **Content:** it is exactly O1's author‑prescribed repair, and exactly one path changed.
- **Scope:** production, schema and SDK bytes are identical to the reviewed head.

## 6. Verification record

- **858 configured tests (review head):**
  - I read the junit directly: 858 tests, 0 errors, 0 failures, 0 skips, across the 22 configured testpaths.
  - The run started at 15:13:40Z, after the last source write at 15:11:16Z, with `source_hash_mismatches: []`.
  - It includes `tests/conformance` and `tests/application/test_learning.py`.
  - It ran on `d6277cc6`, before the supplement. I do not claim a full rerun afterwards.
- **The Opus seat's 894 passed, 12 failed, 7 errors:** that run covered the whole `tests/` tree without `JEVDRILL_AGENT_HARNESS_ROOT` or `JEVDRILL_TEST_CLI`, so its scope and environment differ.
  - Those 19 remain failures of that unconfigured session; I do not claim they disappeared.
  - The configured run, which supplied that environment, has zero failures in those suites.
- **Superseded statements:** the brief's "full suite is running" and `verification.json`'s "Linux only; no new native…" are historical. The junit and the 12:31 native receipts supersede them.
- **Git index:** that it is unchanged is the parent's record. I ran no git commands.

## 7. Grok lifecycle and what that limits

- **Status:** `grok-delivery.json` records `status: cancelled`, `latestTerminalStatus: cancelled`, `hasPendingChildRuns: false` and `standing_completed_seat: false`. Per the parent, no owner‑independent cancellation was requested.
- **Not a vote:** Grok is not a completed governed seat, and its AGREE is not counted.
- **The panel is not clean or unanimous.** It consists of:
  - Astra: completed, AGREE.
  - Opus: completed, PARTIALLY AGREE; both of its items are now closed.
  - Grok: cancelled, but a substantive review was delivered.
  - Gemini was not seated; its excerpt‑only round‑1 approval remains discounted.
- **How I use Grok's review:** only as corroboration where it overlaps code I read or checks I ran, such as the 130 focused tests and parity. It reviewed `d6277cc6`, before the supplement.
- **This ruling does not depend on Grok.** The two completed seats plus my own checks support it. I infer no governed freeze and no formal acceptance.

## 8. Out of scope and unchanged

- **Study‑design questions:** these are unchanged by this delta and were not re‑argued.
  - F6/D3: no re‑derivation of the cheapest feasible model.
  - F7: duplicate call IDs or metric rows are summed.
  - D2: per‑arm attribution depends on arm order.
  - D4: abstentions stop collection.
  - D5: route judgments ignore `allowed_providers`.
  - D6: `offline()` alignment and two‑resource coverage.
- **Needs separate owner action:** empirical tolerances and calibration, any new collection, and any new grant.
  - Q12/Q13 is still unresolved; the validator still emits that error in every loopback run (`test_discovery_calibration.py:472`).
  - The loopback oracle answers 0.9 every time and is not a measurement.
- **Not ratified:** actual experiment counts, tolerances and quality.
- **The old study:** it stays stopped, and its consumed grant cannot validate against the new `source_digest`.

## 9. Non‑blocking notes

These are carried from Opus's review, and I did not re‑argue them.
- **Mutation tests prove binding, not projection:** the `fields` and `projection` tests patch module globals in `jev`, while `application.py:44-50` imports the constant at load. They show the binding invalidates, not that a projection change does. Production shares one object, so this is not a defect.
- **Hashed body vs dispatched body:** the product binding hashes `IsSuitable@build_request` through the `Jev` client. Dispatch goes through `ObserveCandidate` and `typesafe_patch` using the same `IsSuitable@spec` (`baml_src/jev.baml:21-28`). `tests/contracts/test_jev_boundary.py:213-223` shows the two wire bodies are identical.
- **Manual projection versioning:** the product cache relies on bumping `JUDGMENT_PROJECTION_VERSION` when the task text or instruction assembly changes (`application.py:770-782`, `:1051-1094`). This is the binding the round‑2 ruling specified.
- **Forward compatibility:** round‑2 readers reject v2. This is owner‑approved and recorded at `docs/contract-decisions.md:31-33`.
- **The real v1 record is untested:** no test parses the actual stopped‑study v1 record. That it still parses rests on the purely additive widening and the pinned v1 fixtures.
- **Injected v1 record:** a judge returning a v1 record under a v2 policy is caught by the existing check at `application.py:794`, but no delta test exercises it.
- **Doc nits:** `docs/route-interfaces.md:99` still says "unchanged v1 `route_inputs`", and the amendment sits under "Open questions".

## 10. Limitations

- **Not run by me:** ruff, mypy, the package build, and the full suite. Lint and format of the final test file rest on the parent's record.
- **Reducer applied by reading:** I could not recompute `input_digest`, so I checked the reducer's rules against the receipts by reading them.
- **Unverified hashes:** the `/tmp` receipts' recorded SHA‑256 values are unverified by me, although I read their contents.
- **Real database not opened:** profile refusal on the actual Oct‑9 database is shown only by the code path and synthetic tests.
- **No optional‑clause counterfactual of my own:** that rests on static reasoning plus Astra's probe.

## 11. Conclusion

**APPROVE_SCOPED_FIXES.** On the final source `4fb3ed65…fd6b`, the owner‑approved v2 amendment and the carried repairs meet V2‑1 through V2‑4. D1, the fixture‑source binding, the isolated optional‑guidance test, O1 and O2 are closed, and R1–R4 are preserved. The bounded code fix is ready. No blocker remains, and no round 4 is required or authorized.

This ruling excludes:
- governed phase acceptance or a governed freeze;
- empirical acceptance and any count or tolerance ratification;
- study collection, a new grant, or reuse of the consumed grant;
- merge, deployment and publishing.

AGREE
