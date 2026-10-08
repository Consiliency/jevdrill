**Verdict: PARTIALLY AGREE**

The delta answers all nine of my round-1 findings. Eight are fully closed. Finding 1 is closed the way the owner chose: B is expected to stop on the nullable bridge, numeric-only success can't close B, and A and offline C continue. I accept that. One small blocker remains, and the delta introduced it: the plan doesn't say how the expected B stop shows up in the tests. The fix is wording only, and with it I'd AGREE. I made no edits and ran no tests, credentials or provider calls.

## The nine repairs

| # | Round-1 finding | Status | Plan lines |
|---|---|---|---|
| 1 | Nullable stop already met | Answered with the alternative I offered: B is expected to stop and numeric-only success can't close it. See the blocker below. | 71, 146 |
| 2 | Injected adapter bypasses measurements | Answered. Records are populated and projected for both adapters, decision details are the accounting view, and there's an injected-adapter test. No existing code reads `JudgmentRecord.measurements` (searched `src/jevdrill`), so populating it causes no hidden double count. | 61, 63, 89, 146 |
| 3 | Precedence contradicts itself | Answered. Per-counter table, sums over distinct calls, a conflict becomes unknown with an existing reason plus a private diagnostic, synthetic fixtures. | 75–85 |
| 4 | AC7 audit contradicts the planned edits | Answered. Verified snapshot before any edit, allowed-path audit, historical replay runs from the snapshot. | 36, 150 |
| 5 | Two candidates per route not guaranteed | Answered. Guidance goes in required guidance or the task text, never as optional combinations. Every case is checked for exactly one row per model within the real bounds, and preparation stops on truncation. | 114, 149 |
| 6 | Cached reuse double counts | Answered | 63, 89, 146 |
| 7 | No parity proof under `JudgeCandidate-v1` | Answered. Request-body parity, Booleans at 0/0.49/0.5/0.51/1, malformed answers, no repair calls, and a versioned amendment if parity fails. | 87, 146 |
| 8 | Replay diagnostics untested | Answered. Controls for a changed file, a physical-only SQLite rewrite and a changed row, against read-only snapshots. | 120, 149 |
| 9 | Nothing measures beating "always admit" | Answered. The aim is now a descriptive baseline, with a candidate-level outcome join, an always-admit comparison and opposite-usefulness fixtures. | 5, 116, 149 |

## Remaining blocker

**The expected B stop can't close cleanly as written** (AC3 and the suite gate; lines 71, 87, 99, 136, 138).

- **Conflict:** line 71 now runs the checkpoint on an isolated private SDK before any product change, and expects it to stop B. But line 138, which didn't change, puts the checkpoint "in the boundary tests" and says an unavailable observation "must fail … rather than be skipped". Line 136's `automation.suite_command` runs those test files together with A's `test_routing_contracts.py`.
- **Consequence:** on the expected path the implementer has to break one rule:
  - leave the suite red, which blocks the offline C closeout that line 71 allows;
  - skip the test, which line 138 forbids;
  - leave the checkpoint out of the product tests, which also contradicts line 138.

  Running a private SDK inside the product pytest process would also break line 45's rule of one `baml_sdk` per process.
- **Overlapping branches:** line 71's first branch ("direct turn usage is intact and all acceptance fixtures pass → use the helper") can also be true in the expected case. Line 87 defines the explicit-null pass as one request, a kept reservation and a redacted failure. The current code already shows one request and a redacted failure for null (`usage-diagnostics.json:54-68`, `jev.py:90-91`). AC3 settles this in favour of the stop, but the checkpoint paragraph should too.
- **Repair (wording only):**
  1. Say that a null counter failing inside the pinned client stops B whatever the other branches show. Line 87's fail-closed result then becomes evidence for the reproduction, not a pass. Say whether omitted keys and `{}` also stop B.
  2. In the stop state, keep the checkpoint and reproduction out of process, under `.phase-loop/runs/PRE-GEPA-20261005/` and `evidence/EXPERIMENT/pre-gepa-20261005/metering/**`. At most, add a strict-xfail characterization test that flips if the bridge is fixed.
  3. Bind AC3's "blocked" branch to that artifact. Apply line 138 only if B passes the checkpoint, and keep the suites for A and offline C green.
  4. Reword line 99's "verified … metering" for the stop case. It then means the existing unknown accounting plus the runner's per-request reservations.

## Non-blocking

- **Finding 3:**
  - Name which existing `MissingReason` (`contracts.baml:2`) a conflict uses, so AC3 can assert it.
  - Neither `LLMCall` (`ai/events/__init__.pyi:135-143`) nor `Measurement` (`contracts.baml:6-12`) has a call ID, and one `JudgmentRecord` covers both candidates (`jev.py:81-107`). Say that the adapter assigns each candidate's invocation identity internally.
  - An event aggregate whose distinct calls can't be identified should count as incomplete, which is "absent" in the table.
- **Finding 4:**
  - Line 36's "recover verified bytes" should mean recovering into the snapshot only. `application.py` is both inherited uncommitted work and an allowed edit, so the allowed-path audit can't detect it being reset. Diff allowed files against the start snapshot.
  - Any historical replay also needs inputs that `study.py` reads but doesn't hash. These are `tests/contracts/fixtures/route-application.json` (`study.py:41`) and all of `ROOT/src` (`study.py:20,87`).
- **Single schema source (round-1 recommendation):** line 54 makes BAML the source and the dataset's result schemas derived. Lines 42–43 and 50 still put result schemas in the dataset and generate BAML from it. Align them.

Also checked: `scripts/check_import_boundaries.py` exists, and line 61's rule that the adapter can't import `telemetry` matches `vocabulary.yaml:286`.

**Not verified:** the SHA-256 values in `delta-round2.json`, because I have no hashing tool in this read-only session. I did compare the diff hunks against `plan-round2.md` by hand, and they match. I also didn't check whether the current bytes of the study-bound files match `verification.json`.

## Files read

- **Review artifacts:** everything in `research/pre-gepa-review/`: `round1-claude.md`, `reconciliation.md`, `delta-round2.diff`, `delta-round2.json`, `plan-round2.md`
- **Evidence:** in `evidence/EXPERIMENT/routing-comparison-20261005/`:
  - `usage-diagnostics.json`
  - `verification.json` (lines 25–84)
- **Code, read in full:** `src/jevdrill/integrations/jev.py`, `src/jevdrill/telemetry.py`
- **Code, partly read:**
  - `src/jevdrill/application.py` (lines 160–374, plus searches)
  - `src/jevdrill/storage.py` (lines 540–564), plus a search of `src/jevdrill` for code that reads measurements
  - `baml_src/contracts.baml` (lines 2–12 and 219–233)
  - `src/baml_sdk/ai/events/__init__.pyi` (lines 100–158)
  - `src/baml_sdk/ai/__init__.pyi` (`ModelTurn` and usage lines)
  - `docs/vocabulary.yaml` (lines 270–295)
- **Searches and checks only:** `.phase-loop/runs/ROUTING-comparison-20261005/study.py` (searched); `scripts/check_import_boundaries.py` (confirmed it exists)
