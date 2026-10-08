# Detailed plan: fresh bounded accounting smoke

## Task

The owner selected option one on October 2: authorize at most two fresh ordinary
Codex subscription calls, 120 seconds each, no retries, disposable development
tasks and read-only sandbox. This grant is separate from the consumed original
V0 grant. Prices may remain unknown. No API keys, deployment, publication,
automatic learning, policy promotion or full roadmap gate closure is authorized.

## Changes

- Add `scripts/run_accounting_smoke.py`. Reuse the unchanged catalog, strict
  answer check, route fixture and live-input helpers from `verify_v0_release.py`.
  Do not call its original live entrypoint or write its original ledger. Verify
  every COST-v0 source binding and wheel hash before dispatch and reuse its
  isolated installed CLI. Snapshot the new runner and this plan separately.
- Use a new durable attempt ledger under `.phase-loop/runs/SMOKE-v0-20261002/`.
  Record attempts before dispatch, count uncertain/failed attempts as spent,
  replay recorded results without generation, and never renew the grant on rerun.
  Bind the grant to sources, wheel, CLI catalog identity and explicit limits.
- First call: purpose-built JSON readiness task, fresh Linux Codex `exec`, low
  effort, ignore user config, ephemeral mode and 120-second supervised deadline.
  Use config `approval_policy="never"` supported by live exec help so the native
  command remains `codex exec` as required by the unchanged launcher capture.
  Materialize the owned output schema through the real launcher and enable its
  private input/usage capture. Strip API-key/secret environment variables. Keep
  raw JSONL only in memory, retain final synthetic answer and sanitized metadata;
  the launcher uses disposable ephemeral output files rather than retained logs.
- Second call only after the first independently passes: normal installed
  route/adapter/launcher/report path for a different purpose-built JSON task.
  Verify final identity/freshness, input hashes/schema counts, CLI counters and
  selected/applied plan IDs; reopen and drain the queue, inspect durable event
  measurements and exact immutable replay without calling the executor again.
- Add `tests/verification/test_accounting_smoke.py` for durable grant exhaustion,
  replay, interrupted outcomes and source binding rejection. Update
  `docs/v0-deployment.md` with this checkpoint and its limitations. Own only
  `evidence/SMOKE-v0/**`, the new run directory, this plan, its handoff/reflection
  and `plans/manifest.json`; preserve all inherited work and prior evidence.

Read permission includes existing source/test/docs/schema globs, COST-v0 and
INPUT-v0 verification metadata, their referenced wheel and isolated environment,
and exact original `.phase-loop/runs/V0-linux-20261001/live.sqlite3` in read-only
mode for attempt-count comparison. No original operational state is altered.

## Verification

- Focused new smoke-runner tests and changed-file Ruff checks before dispatch.
- `.venv/bin/python scripts/run_accounting_smoke.py` using the validated latest
  installed wheel; verify metadata-only software/source bindings first.
- Repeat the runner once to prove durable replay consumes no further calls.
- Retain `evidence/SMOKE-v0/verification.json`, exact failed/unknown statuses and
  call counts. Do not repeat the unchanged full suite or claim fresh platform
  acceptance from the earlier 833-test software proof.

## Acceptance criteria

- [ ] Grant is durable, bounded to two calls and never renewed on restart.
- [ ] Subscription calls complete within approved posture and pass independent
  answer checks, without model-generated tools or retries.
- [ ] Resolved-input metadata and observed counters travel through actual launch
  and durable installed route/report/replay paths with matching applied identity.
- [ ] Latest installed wheel/source bindings are verified, original ledger is
  intact and raw prices/weights identity/full accounting remain unknown.
- [ ] Evidence and documentation accurately report scope, outcomes and consumed
  attempts; no publication, policy or full-roadmap completion is claimed.
