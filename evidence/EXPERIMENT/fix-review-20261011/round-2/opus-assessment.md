The pinned generation-parity command failed on first run (the compiler exited with status 4, stderr swallowed by the script). Diagnosing that now before running the targeted tests.

Running the five targeted test files now (judge, route integration, JEV boundary, calibration, JEV adapter).

Waiting on the wider five-directory run to finish; checking the remaining D1 binding points in the meantime.

All 17 R1–R4 named cases pass individually. Checking whether the wider directory run has finished, then delivering the verdict.

## Round 2 delta review — Opus seat (R2, R4, D1)

R1–R4 are closed in code and in the targeted tests I reran; no new blocker in the six-file delta. D1 is still open, so this is not a global agreement, and I could not reproduce generation parity in this session.

### What I ran

- **Hashes:** all 11 files match `round-2/source-manifest.json` at the start and end of my review. The base and head manifest digests match `delta-binding.json`. `jev.baml` and the three generated-SDK hashes are identical to round 1.
- **Targeted suite:** the five files give 97 passed.
- **R1–R4 cases by name:** 17 passed (nine driver parametrizations, two route-integration, six missing-usage).
- **Wider run:** `tests/application` plus `tests/integrations` gave 82 passed, 1 failed. The failure is `test_learning.py:298`, the missing-companion case (`JEVDRILL_AGENT_HARNESS_ROOT` unset) also seen in round 1. A five-directory run was still going when I wrote this, so I claim nothing from it.
- **Generation parity — not reproduced:** three attempts with the pinned compiler all failed. The version gate at `check_generated_contracts.py:123-125` passed, then `generate` at `:130` exited with status 4. The script captures stderr and this session denied every way of reading it, so I have no diagnosis.
  - No delta file is a generation input and the generation-related hashes are unchanged, so round-1 parity status carries forward on static grounds only.
  - This contradicts the parent's "parity passes" claim. The president should check `test_generation_is_reproducible` in the parent's full-suite log.
- **Not run:** lint, mypy, the 841-test suite. Read-only throughout; no credentials, no paid calls, no writes.

### Closed

**R1 — closed.**
- `development.py:350` now emits `not_reported`, which is in the enum at `contracts.baml:2`.
- `test_development_judge.py:159-189` covers the six usage shapes for both task and discovery records, with replay equality, exactly two dispatches, and reservations of `(2, 5506)`.
- Unknown cost still fails study validation: `metric()` returns `None` (driver `:445-446`), the arm cost becomes `None` (`:805-809`, `:1483-1485`), and the validator rejects it (`:452-453`, `:895-899`). That rests on the existing `unknown` fault at `test_discovery_calibration.py:167-168`, not on a new end-to-end test.

**R2 — closed.**
- The judged payload is an allowlist at `application.py:745-780`. It omits `guidance_options`, `cost`, `rates`, `default`, `source`, `source_version` and `token_counter_revision`.
- The candidate ID suffix is derived from the selected optional refs only (`:1050`), and nothing else recomputes `candidate_digest`.
- `test_route_integration.py:310-316` asserts that no unselected option's ID, revision, hash or role appears; `:317` keeps the four combinations distinct; `:318-322` shows the unguided row is identical with options populated or cleared.
- The driver test pins reuse for honest runs: `no_guidance` and `fixed_default` have no judgment calls (`test_discovery_calibration.py:481-484`).
- No prompt change.

**R3 — closed.** The synthetic requirement is satisfied in test data only (`test_route_integration.py:239`). All-false gives four exclusions, each exactly `quality_unknown_or_insufficient`; true gives `ready` (`:256-262`).

**R4 — closed.**
- The validator builds the task-required set at driver `:720-728`. It mirrors the application's linked-route merge at `application.py:971-992` (discovery-required first, then request-active, de-duplicated by resource, task ID rebound), so the rule is right for a non-empty set too.
- Conditions at `:838-855`: optional guidance is forbidden on all four baselines, non-retrieval arms must equal the task-required set, and `simple_retrieval` must equal the retrieved refs exactly, including revision, hash, role, admission, authority and task.
- Constructors at `:1296-1313` preserve the actual plan's required guidance.
- Nine parametrizations pass with the error set pinned exactly (`test_discovery_calibration.py:453-461`).

### Non-blocking observations

1. **The "exact key-set" pin is 25 keys; the allowlist is 26.** `execution_token_limits` is allowed at `application.py:765` but missing from the test's set at `test_route_integration.py:272-298`. The test passes only because `route-application.json` has no such field; the driver sets it at `:1208`. It is a legitimate limits field, not a leak, but two hand-copied sets that already disagree will not catch a future addition. A single named constant fixes this and is what D1's projection binding needs anyway.

2. **The "optional fallback" mutation does not exercise the optional-forbidden rule.** The test itself asserts the mutated plan has no guidance at all (`test_discovery_calibration.py:477-480`), so the error comes from `required != retrieved` (driver `:850-851`), the same branch as omission. No parametrization produces a baseline plan with optional guidance, so the clause at `:839-841` is verified by reading only. All five sub-conditions share one error string, so the exact-set pin cannot tell branches apart. This is the same shape as round-1 F3.

3. **The validator's expected refs now depend on files outside the study source digest.** `inputs()` reads `tests/contracts/fixtures/discovery.json` and `route-application.json` (driver `:103-145`); `source_digest` (`:313-330`) does not cover `tests/`. Round 1 compared IDs from the protocol, which is covered. Not a problem on the frozen fixtures; add both files to the digest before the freeze.

4. **Reuse is not asserted for `cheapest_feasible`**, though it is applicable in every case and should be equally deterministic.

5. **`verified_at` and `expires_at` remain in the judged payload**, so receipt identity is tied to wall-clock time. The driver sets one timestamp per case (`:1215`), so pairing within a case is unaffected.

### Still open, not part of the repair scope

**D1 (owner decision) — pending, blocks the source freeze.**
- The label is still `JudgeCandidate-v1` at `development.py:410`, `contracts.baml:154,164` and driver `:1189`.
- R2 changes the judged payload a second time under that label.
- Nothing binds the prompt or projection: not the judge revision (`development.py:159-175`), the validator's expected value (driver `:670-686`), or the route cache key (`application.py:604-613`).
- `docs/route-interfaces.md:75-79` still documents only the discovery payload, with no line that instruction bodies of offered combinations reach the judgment provider.
- I am not waiving this.

**D2 (attribution) — unchanged policy, now pinned by a test.** Honest runs give `no_guidance` and `fixed_default` zero navigation calls and cost (`test_discovery_calibration.py:483-484`). Any owner change to attribution will have to change that assertion.

**Inherited, unchanged:** F6/D3; F7 (`objective_tokens` at `:488-492` still has no `disjoint` filter or duplicate guard, unlike `metric()` at `:443`); D4–D6.

None of this is empirical evidence: the loopback oracle answers 0.9 unconditionally. I ratify no study acceptance, grant, or collection-policy change.

PARTIALLY AGREE

The five-directory run has now finished, so I can replace the "still going" line in my review with a result. Nothing else in the review changes.

**Five targeted directories** (`tests/experiments`, `tests/application`, `tests/contracts`, `tests/verification`, `tests/integrations`): 585 passed, 1 failed, 1 deselected.

- **The failure** is `tests/application/test_learning.py:298`, the missing-companion case (`JEVDRILL_AGENT_HARNESS_ROOT` unset). It is the same environment failure seen in round 1 and in my narrower run, not a regression from the delta.
- **The deselected test** is `test_generation_is_reproducible`, which I excluded because the pinned compiler exits with status 4 in this session. Generation parity therefore remains not reproduced by this seat.

R1–R4 stay closed, the five non-blocking observations stand, and D1 remains the open owner decision blocking the source freeze. No empirical acceptance is ratified.

PARTIALLY AGREE
