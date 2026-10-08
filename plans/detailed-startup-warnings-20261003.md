# Detailed plan: accept validated Codex startup warnings

## Task

The owner approved continuing with the recommendation to plan and test startup
warning handling offline. Reuse the assigned JEV/companion dirty worktrees;
preserve inherited changes. Local implementation only, no publication. Both
existing live grants are exhausted; no provider call or ledger write is allowed.

## Research summary

DIAG-SMOKE-v0 rejected item.completed at stage 1, after thread.started but before
turn.started. Its subtype/message were discarded, so it cannot prove a benign
warning. Pinned openai/codex rust-v0.159.2 serializes configuration warnings,
warnings and deprecation notices as completed error items; fatal errors use the
top-level error event. Model reroutes and announced dropped events are also
error items with fixed prefixes and must continue to invalidate capture.
Source: codex-rs/exec/src/event_processor_with_jsonl_output.rs at rust-v0.159.2.

## Changes

- Companion phase-loop-runtime/src/phase_loop_runtime/launcher.py: classify
  fixed item types before state-order rejection. At stage 1 accept only an
  item.completed error with exactly one nonempty string id/type/message and no
  extra fields. Retain thread/turn order, active-turn opaque items, counters,
  subset/zero validation and rejection on malformed/rerouted/dropped data.
  No warnings are accepted before the thread or after its terminal. Classify
  early reroute/drop notices with the existing fixed reasons, without their text.
  Version the collector method to codex_exec_jsonl_0_159_2_v2.
- Companion phase-loop-runtime/src/phase_loop_runtime/jevdrill_adapter.py:
  register both v1 and v2 methods with identical measurement constraints;
  reject mixed-method receipts. Preserve v1 delivery/replay compatibility.
- Companion phase-loop-runtime/tests/test_jevdrill_diagnostics.py and
  test_jevdrill_usage.py: startup success, repeated warnings, missing/duplicate/
  extra/nonstring fields, early unknown/tool/collaboration items, rerouting,
  dropped events, before-thread/after-terminal ordering, unchanged counter
  failures, real synthetic launcher preservation and v1/v2 adapter compatibility.
- JEV tests/conformance/test_usage_reporting.py: startup-warning and early-drop
  synthetic cases through installed CLI, actual adapter, queue restart,
  acknowledgment loss and SQLite replay; assert v2 method/privacy and unknown
  on loss. Existing cases remain intact.
- JEV scripts/verify_executor_input.py: --startup-warnings in a new STARTUP-v0
  scope/plan/run/evidence. Require complete unskipped diagnostic controls, fresh
  companion regressions, frozen refresh, wheel installation and full JEV tests.
  Preserve all historical proofs and live runners. The new artifact covers
  only current software and synthetic fixtures, not historical live acceptance.
- Docs: companion docs/jevdrill-integration.md and JEV docs/host-interfaces.md,
  docs/v0-deployment.md document exact warning rules, v2, limits and exhaustion.
  Add v2 external identifier alongside historical v1 in docs/vocabulary.yaml;
  regenerate docs/vocabulary.md. No BAML or metric-version change: existing
  token counting semantics remain unchanged.
- Own this plan, plans/manifest.json, evidence/STARTUP-v0/**,
  .phase-loop/runs/STARTUP-v0-20261003/** and new execution handoff/reflection.

Read permission includes repo source/test/docs/schema/scripts/locks and pinned
CLI source, evidence/{DIAG-v0,DIAG-SMOKE-v0,SMOKE-v0}/**, historical verification
JSON, starting snapshots and ledger files strictly read-only for hash checking.
No raw provider data or credentials are needed. No other files are owned.

## Verification

First reproduce rejection of a synthetic pre-turn warning. After edits run
companion usage/diagnostics tests with its source/test PYTHONPATH. Then:

`BAML_CLI=/mnt/workspace/worktrees/viperjuice/.baml-v1-0201-toolchain/bin/baml-cli JEVDRILL_AGENT_HARNESS_ROOT=/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port .venv/bin/python scripts/verify_executor_input.py --startup-warnings`

This is the automation.suite_command. It must verify isolated installed
transport and full JEV tests, vocabulary generation/lint and changed JEV format.
Hash all previous artifacts and both exhausted ledgers to prove preservation.
No live CLI execution/replay runner is invoked after source bindings change.

## Acceptance criteria

- [ ] Validated pre-turn warnings yield v2 counters through the real synthetic
  launcher; active-turn/counter semantics and privacy remain intact.
- [ ] Startup malformed, unknown/tool/collaboration/reroute/drop and invalid
  ordering cases fail closed, with fixed subtype/reason diagnostics.
- [ ] v1/v2 report validation and installed v2 reporting, restart, duplicate
  acknowledgment and exact replay pass; mixed receipt methods are rejected.
- [ ] Fresh STARTUP-v0 software proof passes all required controls and full
  suite with immutable bindings; historical evidence and ledgers stay unchanged.
- [ ] Docs, dirty-path classification and reflection reflect software readiness
  and continuing failed live acceptance; no renewed call authority is inferred.
