# Detailed plan: repair native acceptance verification

## Task

Continue the authorized roadmap execution by fixing failures reproduced by the
original native collectors. This is a bounded continuation of the reconciliation
plan. No provider call, security change, publication or promotion is included.

## Research summary

The expanded Windows suite exhausted the LEARN collector's 300-second budget.
Its timed-out installed-package subprocess left a descendant holding the temporary
directory. The Linux HOST companion run passed 137 assertions and failed one:
the observability fixture retained a private absolute plan path, so the validator correctly
rejected its absolute private plan path. Actual product assertions remain required.

## Changes

- `scripts/verify_route_phase.py`: add one bounded subprocess helper for offline
  verification. Reject an expired budget before launch; on timeout terminate the
  launched process group on Unix or its process tree on Windows, wait for cleanup,
  and retain timeout failure. Use it in the existing ROUTE collector. Set its
  offline collector/reducer bound to 600 seconds, matching the expanded HOST proof.
- `scripts/verify_learn_phase.py`, `scripts/verify_experiment_phase.py`: use that
  helper and a 600-second offline proof limit. Keep reducer rejection for exceeded
  or nonfinite durations. Routing and experiment execution limits stay unchanged.
- `scripts/verify_v0_release.py`: set the offline software command timeout to
  600 seconds so the same expanded suite can complete. Live grant limits remain
  unchanged. In reconciliation, flag any single-node collection exceeding roughly
  five minutes, as required by the existing roadmap; retain actual elapsed times.
- `tests/verification/test_route_phase.py`: verify timeout cleanup with a real
  controlled subprocess and verify that an expired allowance launches nothing.
- `tests/verification/test_learn_phase.py`,
  `tests/verification/test_experiment_phase.py`: verify acceptance at 600 seconds
  and rejection above the bound or for invalid durations.
- Companion `phase-loop-runtime/tests/test_phase_loop_work_unit_observability.py`:
  build the existing synthetic closeout with a repository-relative plan path and assert
  that its closeout passes the real metadata validator before event extraction.
  Synchronize public source/test copies in the owned native regression fixtures.
- `evidence/ROADMAP/**`, `.phase-loop/runs/ROADMAP-20261003/**`: preserve failed
  native cohorts, logs and original bytes; collect fresh original verifier reports.
- `plans/manifest.json`, `.dev-skills/handoffs/**`: lifecycle and continuation.

Read allowance: these public files, the parent plan's source/test/config allowance,
and exact controlled logs/reports under the owned ROADMAP run directories on Linux,
macOS and Windows. Existing live ledgers remain hash-only; no credentials or raw
provider transcripts are read.

## Documentation impact

Record verification limits and failure diagnosis in ROADMAP evidence. No public
contract or frozen vocabulary changes are introduced. The parent deployment and
roadmap documentation will link the final current acceptance records.

## Dependencies and order

1. Archive failed metadata and inspect controlled diagnostic output.
2. Repair fixtures and bounded collection; run targeted controls.
3. Freeze source, synchronize native candidates, run original collectors/reducers.
4. Return to the parent package refresh and EC reconciliation.

## Verification

- `.venv/bin/python -m pytest -q tests/verification/test_route_phase.py tests/verification/test_learn_phase.py tests/verification/test_experiment_phase.py tests/verification/test_host_phase.py`.
- Companion pytest on `tests/test_phase_loop_work_unit_observability.py`, followed
  by the original HOST companion selection through the owned regression fixture.
- Ruff check and format check for the changed scripts and verification tests.
- Original native CONTRACT, ROUTE, HOST, LEARN and EXPERIMENT collectors/reducers;
  EXPERIMENT remains blocked when production operational evidence is missing.
- `git diff --check` in both owned worktrees.

automation.suite_command: .venv/bin/python -m pytest -q tests/verification/test_route_phase.py tests/verification/test_learn_phase.py tests/verification/test_experiment_phase.py tests/verification/test_host_phase.py

## Acceptance criteria

- [ ] Expired verification budgets start no command; timed-out controlled parent
      and child processes stop before temporary-directory cleanup.
- [ ] ROUTE, LEARN and EXPERIMENT reducers enforce their 600-second finite proof
      bound; the reconciliation flags collections exceeding roughly five minutes.
- [ ] The companion fixture validates and its event metadata assertions pass.
- [ ] Failed native cohorts stay archived, and current acceptance uses original
      reducers with actual source bindings and no skipped required assertions.
