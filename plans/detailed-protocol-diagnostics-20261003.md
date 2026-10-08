# Detailed plan: metadata-only protocol diagnostics and remaining smoke call

## Task

The owner authorized adding diagnostics and trying again on October 3. Use the
one remaining call in the October 2 two-call grant: 120 seconds, subscription
login, read-only sandbox, disposable task, no further retries or grant reset.
Preserve the original V0 ledger and the fresh grant's protocol and first attempt.
Reuse the assigned dirty JEV and companion worktrees; publication stays local.

## Changes

- Companion launcher: add host-local `jevdrill_protocol_diagnostics` to
  LaunchResult, enrichment and event metadata. The stdout collector retains only
  closed-vocabulary event/item categories, bounded counts of records through the
  first rejection, stage and fixed rejection reason. Reader/drain failures keep
  first-reason precedence. Record disabled capture when probe/path is unsupported.
  Keep parsing/receipt acceptance rules unchanged; no raw text, IDs, keys, paths,
  unknown strings or exception payloads enter diagnostics or BAML reports.
- Add companion `phase-loop-runtime/tests/test_jevdrill_diagnostics.py` covering
  known/unknown/duplicate/opaque/announced-drop/zero/missing/probe/reader paths,
  result preservation and privacy. Update companion docs/jevdrill-integration.md
  and JEV docs/host-interfaces.md and docs/v0-deployment.md.
- Extend scripts/verify_executor_input.py with --diagnostics, a DIAG-v0 plan/run/
  evidence scope and the diagnostic suite alongside all existing companion
  controls, isolated wheel installation, frozen refresh and full JEV tests.
  Preserve all older proof artifacts; new current-source proof is required.
- Add scripts/run_protocol_diagnostic.py and
  tests/verification/test_protocol_diagnostic.py. Reuse helpers from the frozen
  original smoke runner without modifying it. Bind the new current software
  artifact, runner and plan in an append-only diagnostic_authority row in the
  existing fresh grant database. Verify the original protocol against its saved
  authorization and both ledger hashes/attempt counts before reserving. Consume
  the second attempt as `diagnostic`, never overwrite readiness or renew the cap.
  Run one purpose-built routed task through the actual installed CLI, adapter,
  launcher and durable reporting queue. Retain sanitized diagnostics, final
  synthetic answer, counters, input hashes, queue/replay and failure statuses.
  Restart must replay its recorded outcome without another call. Report failed
  usage honestly; the owner's authority is exhausted after this attempt.
- Own evidence/DIAG-v0/**, evidence/DIAG-SMOKE-v0/**, this plan, manifest,
  .phase-loop/runs/DIAG-v0-20261003/**, handoff/reflection and the diagnostic
  authority/attempt append to .phase-loop/runs/SMOKE-v0-20261002/grant.sqlite3.
  Do not edit original smoke artifacts or the original V0 database.

Read permission includes source/test/docs/schema/contract globs and locks,
evidence/{COST-v0,INPUT-v0,SMOKE-v0}/verification.json, SMOKE authorization/
readiness metadata, referenced wheels/environments and original V0 live.sqlite3
read-only. No old raw provider evidence is needed. BAML contracts stay unchanged.

## Verification

- Focused diagnostic and grant tests; changed-file lint/format checks.
- `BAML_CLI=/mnt/workspace/worktrees/viperjuice/.baml-v1-0201-toolchain/bin/baml-cli JEVDRILL_AGENT_HARNESS_ROOT=/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port .venv/bin/python scripts/verify_executor_input.py --diagnostics`.
- Live CLI help/subscription preflight, then
  `.venv/bin/python scripts/run_protocol_diagnostic.py`; replay once without a
  generation. Preserve failures and counts in evidence/DIAG-SMOKE-v0/verification.json.
- Classify final paths/digests, record docs and reflection. No commit/deployment,
  policy promotion, invoice claim or full roadmap gate closure.

## Acceptance criteria

- [ ] Closed-vocabulary diagnostics explain acceptance/first rejection or
  disabled capture without persisting raw data or altering usage semantics.
- [ ] Local diagnostics/launcher and full JEV verification pass with installed
  wheel and current source bindings; no older evidence is overwritten.
- [ ] Remaining attempt is durably reserved, bounded to 120 seconds and never
  replayed as another generation; original ledger/protocol/readiness stay intact.
- [ ] Routed live outcome, usage validity, diagnostics and durable delivery/replay
  are recorded accurately, including failed/unknown values.
- [ ] Documentation and closeout state actual results and limits; any still-failed
  live usage blocks release acceptance and no further call authority is inferred.
