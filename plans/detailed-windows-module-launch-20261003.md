# Detailed plan: reliable native Windows CLI invocation

## Task and research

Continue roadmap acceptance without a purchase or security change. Windows Smart
App Control intermittently rejects unsigned launchers generated in fresh wheel
installations (WinError 4551). The installed interpreter successfully runs
`-m jevdrill.cli`, and the production host transport already accepts an argv prefix.

## Changes

- `tests/contracts/test_package.py`: exercise installed module invocation on
  Windows outside the checkout; retain console-script coverage on Unix.
- `tests/conformance/test_usage_reporting.py`: use the installed JEV interpreter
  on Windows for actual transport and replay. Keep the separate companion
  interpreter, native execution and unsupported telemetry assertions intact.
- Companion `phase-loop-runtime/tests/test_jevdrill_adapter.py`: use the same
  Windows prefix in the actual installed transport test.
- `docs/host-interfaces.md`, `docs/v0-deployment.md`, `docs/roadmap-status.md` and
  companion `docs/jevdrill-integration.md`: document explicit Windows configuration
  and the preserved launcher failure; reconcile current roadmap pointers.
- `evidence/ROADMAP/**`, native phase reports, `evidence/V0-refresh/**`, private
  ROADMAP run directories, manifest and handoffs: preserve prior cohorts and
  collect final source-bound native reports and Linux package refresh.

Read allowance includes these files, existing collectors, their declared public
inputs and owned native fixture copies. Existing live ledgers remain hash-only.
No production API, schema, permission, security setting or provider call changes.

## Verification

1. Verify actual native installed module invocation before editing tests.
2. Run installed-package and reporting/replay tests on native Windows; run
   targeted Linux assertions and format/lint checks for changed Python files.
3. Freeze and synchronize all declared inputs, including evaluation cases. Run
   original CONTRACT/ROUTE/HOST/LEARN/EXPERIMENT native collectors and reducers.
   Preserve failures and any missing operational EXPERIMENT evidence.
4. Refresh Linux V0 installation/upgrade/replay and prepare exact handoffs.

## Acceptance criteria

- [ ] Windows installed module works under existing Smart App Control.
- [ ] Actual reporting/replay assertions pass without skipped required cases.
- [ ] Current platform evidence has matching source digests; incomplete phase
      gates remain explicit. No paid call, activation or publication occurs.

automation.suite_command: .venv/bin/python -m pytest -q tests/contracts/test_package.py tests/conformance/test_usage_reporting.py
