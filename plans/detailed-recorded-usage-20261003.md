# Detailed plan: integrate the recorded Codex usage receipt

## Task

Continue the approved V0 recommendation offline. Reuse the assigned dirty JEV
worktree and read the assigned companion source/tests without modifying it.
Preserve inherited changes, historical proofs, frozen runners and all three
exhausted grant ledgers. No provider generation, deployment or publication.

## Research summary

The approved startup call completed with a valid v2 receipt, but its frozen
checker hashed unsorted schema JSON without the launcher's trailing newline.
Offline reanalysis matched the actual materialized bytes. The existing installed
conformance probe already tests queue restart, acknowledgment loss, duplicate
delivery, privacy and exact SQLite replay. Extend that probe with the captured
receipt as an explicitly recorded fixture under synthetic execution.

## Changes

- tests/conformance/fixtures/codex-0.159.2-v2-usage.json: retain the sanitized
  captured receipt, the exposed schema and original result digest, with explicit
  provenance. No task/output text or raw protocol stream.
- tests/conformance/test_usage_reporting.py: add recorded_usage using locally
  reconstructed protocol events and exact receipt equality. Check the actual
  materialized schema/prompt fingerprints, persistent measurements, restart,
  duplicate acknowledgment and replay. Keep observed counts separate from new
  synthetic execution timing and explicitly label the fixture's provenance.
- scripts/verify_executor_input.py: add a strict prepared-manifest comparator
  matching materialized sorted JSON plus newline, and --recorded-usage under
  REPORT-v0. Require the new conformance artifact, existing startup/input
  controls, fresh installed wheel/full suite and source bindings. Do not
  overwrite historical evidence/STARTUP-v0/verification.json.
- tests/verification/test_executor_input.py: negative controls for changed
  prompt/schema, missing/unknown observations, wrong scope and old serialization.
- docs/host-interfaces.md and docs/v0-deployment.md: record the confirmed direct
  executor capture and the new offline bridge proof; preserve their distinct
  provenance and remaining release limits. No BAML, metric or vocabulary change.
- Own this plan, plans/manifest.json, evidence/REPORT-v0/**,
  .phase-loop/runs/REPORT-v0-20261003/** and new handoff/reflection files. Create
  a corrected version of the private startup guard in the new run root; leave
  it unapproved, unprepared and unexecuted. Test its checks offline.

Read allowance: repo source/tests/docs/schemas/scripts/locks, assigned companion
source/tests, evidence/STARTUP-v0/**, and .phase-loop/runs/STARTUP-v0-20261003/**.
Read the original V0 and SMOKE grant ledgers only to hash them. No secrets/raw
provider data are needed. Historical source-binding proofs remain historical
after these edits; current software must be verified again under REPORT-v0.

## Documentation impact

Update host/deployment notes with actual scope and limits. The frozen contract
uses source host, scope run, disjoint input/output, cached-input as a subset of
input, and reasoning as a subset of output (docs/host-interfaces.md). These
semantics remain unchanged. A known zero stays known; raw price stays unknown.

## Dependencies & order

Hash historical inputs first. Add the fixture, comparator and probe together,
then update docs. Run targeted controls before the complete verifier. Record
local closeout and retain all failed historical verdicts. No gate amendment
substitutes this offline probe for a new live routed execution.

## Verification

Targeted: .venv/bin/python -m pytest -q tests/verification/test_executor_input.py;
run recorded_usage with the previously installed wheel and companion.

automation.suite_command:

`BAML_CLI=/mnt/workspace/worktrees/viperjuice/.baml-v1-0201-toolchain/bin/baml-cli JEVDRILL_AGENT_HARNESS_ROOT=/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port .venv/bin/python scripts/verify_executor_input.py --recorded-usage`

The runner disables real providers, refreshes frozen dependencies, installs an
isolated wheel, verifies companion input/startup controls, vocabulary/lint/format,
the recorded fixture and the complete JEV suite without skips. Hash checks before
and after prove that previous ledgers, frozen runners and verification artifacts
remain intact. Test the corrected guard's authority/replay without generation.

## Acceptance criteria

- [ ] Captured receipt metadata/counts persist exactly through the installed
  adapter/queue, restart, duplicate acknowledgment and SQLite replay; replay
  dispatches no executor. Proven by recorded_usage artifact and full runner.
- [ ] The comparator matches actual materialized schema/prompt bytes and rejects
  missing, changed or unsupported observations. Proven by targeted controls
  and recorded_usage, including its actual local child process.
- [ ] Fresh REPORT-v0 software evidence passes the complete suite and required
  controls with current immutable bindings. Proven by suite_command.
- [ ] All historical evidence, frozen runners and three exhausted ledgers stay
  unchanged. The corrected guard has no approval/proposal/ledger or generation.
  Proven by preservation hashes and its offline guard controls.
- [ ] Docs/closeout label recorded receipt plus synthetic execution accurately;
  costs, quality claims, integrated live acceptance and full gates remain open.
