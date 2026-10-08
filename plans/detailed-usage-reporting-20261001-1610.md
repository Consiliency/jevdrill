# Detailed plan: observed Codex usage in JEV Drill reports

## Task

Implement the first recommendation from the October 1 investigation: retain
observed Codex token counters through the normal Linux harness launch and JEV
Drill reporting path. This is one bounded change across Consiliency/jevdrill and
Consiliency/agent-harness. Delivered-input accounting and cost estimation require
separate follow-up plans.

This invocation authorizes planning only. Default mode is active; Plan Mode was
not active. No runtime implementation, tests, generators or builds run during
planning. Future execution is local only: no model generation, paid call,
deployment, publication, commit, merge, fleet-default change or policy promotion
is authorized by this plan. Preserve the exhausted live-study ledgers.

## Research summary

`JevDrillAdapter.launch` currently emits unknown token measurements despite the
release smoke retaining CLI counters separately. `LaunchResult` and
`_result_with_spec` provide the seam for preserving a normalized usage payload.
The supervised Linux launcher merges stdout and stderr; trustworthy capture must
observe the CLI's stdout channel before combining presentation output. Existing
BAML report contracts, strict schema validation and the persistent queue are
sufficient for delivering the registered measurements without a wire change.

Input checkouts:

- JEV Drill: `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux`, branch
  `codex/v0-linux`, input HEAD `77d41b2c655413ea183eaf72153bfaea60dc42c5`.
- Companion: `/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port`,
  input HEAD `56dce95a52625a58cd08911f8f623c637bf52e44`. Preserve its existing
  Windows and other unrelated work; this plan changes no Windows backend.
- Findings: `research/runtime-accounting/investigation-20261001.md` and its
  observations file. No original V0 source, ledger or evidence is rewritten.

Additional pinned upstream research resolved terminal-counter semantics:
`openai/codex` tag `rust-v0.159.2`, input commit
`ff6aec96948b70d94983af2641a6b67c94faeff5`,
`codex-rs/exec/src/event_processor_with_jsonl_output.rs`,
`usage_from_last_total` and `ThreadTokenUsageUpdated` handling. It emits the
latest cumulative thread totals, and emits `Usage::default()` if no update
arrived. Therefore all-zero terminal usage is ambiguous, and cumulative updates
must not be summed. Copies of this source, `exec_events.rs` and `protocol.rs`
are retained under `.phase-loop/runs/PLAN-usage-reporting-20261001-1610/`.
`inputs.json` records their hashes and the current report-schema/companion inputs.
Additional review research pins `codex-rs/exec/src/lib.rs` at the same commit in
`research/usage-review/upstream/exec-lib.rs` (SHA-256
`48be5b8d89283f1fe338682d634ea3e73847ef1eb7c7626ca801002980527de1`).
Its dispatch filter and token-update predicate bind notifications to the active
root thread and turn. This establishes attribution, not complete accounting.

## Advisor review amendments

The four-seat manual advisory review and Opus president ruling are recorded in
`research/usage-review/`. This review authorizes no implementation or governed
gate closure. The president requires these changes before execution:

- A1: define CLI-reported totals and document unobservable accounting residuals.
- A2: make invalidation permanent, distinguish clean EOF from reader failure,
  and accept the genuine duplicate-ID web-search item shape as opaque content.
- A3: report timeout/stall as failed even after a graceful zero exit.
- A4: enable capture only with a private adapter opt-in, never from `--json` alone.
- A5: require the launcher seam, completion-proof and LaunchSpec regression suites.

The changes below incorporate those amendments. See
`research/usage-review/reconciliation.md` for deferred suggestions and follow-ups.

## Frozen protocol and terminology

Re-use these BAML lines from `baml_src/contracts.baml`, read during investigation:

```baml
class Measurement {
    metric_id: string, metric_version: string, measurement_value: MeasurementValue,
    source: "direct" | "provider" | "host" | "evaluator" | "estimate",
    method: string, scope: "call" | "run" | "task" | "experiment",
    counting_semantics: "disjoint" | "subset" | "not_applicable",
    parent_metric_id: string?,
}
class UsagePayload { kind: "usage", measurements: Measurement[] }
```

`ExecutionEvent` retains `event_id`, `execution_run_id`, `source_id`,
`source_sequence` and `supersedes_event_id`. `ReportAccepted` and `ReportDuplicate`
require `durable: true`. Their meanings and all version-1 wire schemas stay
unchanged. BAML remains the contract authority; do not introduce a second Python
or TypeScript wire contract or mix the two repositories' BAML runtime versions.

No new domain vocabulary is introduced. Re-use `input_tokens`, `output_tokens`,
`cached_input_tokens`, `reasoning_tokens`, `UsagePayload`, `ExecutionRun` and
`ReportRequest`. Register the one host-owned method identifier
`codex_exec_jsonl_0_159_2_v1` as an external identifier in the vocabulary registry.
It means the latest cumulative total reported by the CLI for the supported
fresh-thread path. `scope="run"` attaches the observation to its ExecutionRun;
it does not certify complete run/task accounting. Stdout cannot certify coverage
of compaction, internal review/compact/memory/guardian sub-agents, suppressed
collaboration tools/states, provider retries, unannounced internal notification
filtering or mid-thread total resets. Announced event drops are observable and
must invalidate capture, rather than being treated as residual coverage. Both
integration documents must make this distinction.
A known zero means a CLI-reported zero; it does not establish independently
measured provider cache/reasoning absence or invoice-level usage.

## Behavior to implement

1. Capture only standard Linux Codex `exec` launches with native version
   `codex-cli 0.159.2`, a fresh thread and JSONL output. An active JEV adapter
   requests `json_output=True` before launch construction for Codex, then passes
   the private `codex_usage_capture=True` kwarg to `launch_with_spec` at the bound
   adapter launch. Its default is false. Probe, stream split and receipt capture
   require that opt-in, executor Codex, Linux and a live launch. `--json` alone
   never enables capture. Dry run, recursion bypass, other executors and launches
   without the adapter preserve their existing behavior. Unsupported versions
   retain the ordinary executor outcome with requested JSON mode, but usage stays
   unknown; capture does not promise that an incompatible CLI will succeed.
2. Probe the actual selected CLI with argv-based `--version`, timeout at most one
   second, without shell interpretation or inference. Perform the probe inside
   the existing timed launch, deduct its elapsed time from any execution deadline
   and never extend that deadline. A failed probe disables known usage, not the
   ordinary executor. If the deadline expires, use the existing unavailable or
   timeout behavior rather than dispatch outside it. Use the same selected CLI
   and actual child environment/PATH for probing and dispatch. Own the probe's
   process session/group, clean up its descendants on timeout, and bound pipe
   shutdown so a wrapper child cannot hold the launch indefinitely. Keep recorded
   executor argv unchanged. Do not cache the probe. Existing completion_time_ms
   remains the host-monotonic wall time of the launch call, including preparation
   and the probe; do not subtract overhead or add a timing metric.
3. Observe stdout separately from stderr on the opted-in supervised Linux path.
   Pass the optional observer through lease-supervisor recursion. Linux ephemeral
   monitoring creates a local temporary log; Windows recursion stays unsupported.
   Tag each stream's records and give clean EOF and reader errors distinct tags.
   After process exit, consume queued records until both streams reach clean EOF
   under the existing bounded shutdown policy; an empty queue or joined thread
   alone does not prove drainage. Read/decode failure or an incomplete/timed-out
   drain invalidates usage. Preserve combined output content, logs, heartbeat,
   custody and cleanup behavior. The default observer-free path stays unchanged.
4. Parse JSONL without overwriting duplicate authoritative keys, with a one-MiB
   per-record parsing limit. Every nonempty stdout line must be a valid,
   classifiable top-level event from the pinned protocol. Duplicate-key/number
   strictness applies to the event envelope, usage and the single `item.type`
   discriminator. Accept the pinned fifth usage key `cache_write_input_tokens`
   without mapping it to a metric. Positive fixtures use that genuine five-key
   shape. Other item content is opaque: genuine web_search records have
   duplicate nested `id` keys from upstream serde flattening and remain accepted.
   Do not inspect opaque payloads as protocol events or copy them into receipts.
   Malformed, oversized, non-finite or unclassifiable protocol records, duplicate
   authoritative keys, non-protocol stdout text, serialization-error substitutes,
   reader errors and incomplete drainage put the collector into a permanent
   invalid state. Later valid terminal records cannot restore known usage.
   Retain one terminal cumulative snapshot, never a sum. Require one thread start,
   one turn start and one terminal completion with usage. Multiple starts or
   terminal records or observable collaboration/child-agent items invalidate
   usage. For `error` items only, inspect one classifiable string `item.message`
   for the pinned notice prefixes `model rerouted: ` and
   `in-process app-server event stream lagged; dropped `; either permanently
   invalidates capture. Duplicate/malformed message discriminators are invalid.
   This narrow exception does not inspect other opaque item content or copy the
   message into a receipt. Resume/fork are structural argv
   exclusions. Compaction absence cannot be established from this stream and is
   not a collector rejection guarantee.
5. Re-use the registered four token metric IDs. Map CLI `reasoning_output_tokens`
   to `reasoning_tokens`. Present counters must be exact integers from zero
   through `2**53 - 1`; reject booleans, negatives, fractions and non-finite or
   unrepresentable values. Reject a snapshot whose cache/reasoning subsets exceed
   their parent or whose subset parent is absent. Missing optional categories stay
   unknown. An all-zero available snapshot stays unknown because upstream can
   synthesize it; zero categories in an otherwise valid nonzero snapshot remain
   known zero. Do not infer cache-write counters or introduce a new metric here.
6. A validated snapshot uses `source="host"`,
   `method="codex_exec_jsonl_0_159_2_v1"`, `scope="run"`, and metric version `1`.
   Input/output are disjoint; cache/reasoning are subsets with their existing
   parent IDs. This records what the CLI reported. Missing or ambiguous usage uses
   the existing unknown/not-reported values. Quality and prices remain unknown.
   Missing terminal usage after cancellation or failure stays unknown; do not
   estimate spent tokens. A valid observed snapshot may survive a later process
   failure, while that run remains failed and receives no completion claim.
   Fix the adapter's existing terminal classification: interrupted means canceled;
   timed_out or stalled means failed even if shutdown produces returncode zero;
   failed/unavailable results mean failed; only the remaining success case means
   completed. Preserve existing selected/applied identity rules: failure alone
   does not null applied_plan_id for an available, identity-matching execution.
7. The host stores a `UsagePayload`-shaped JSON mapping in optional
   `LaunchResult.jevdrill_usage`, preserving it through `_result_with_spec`.
   This is a host-local carrier for the existing BAML contract, not a new exported
   wire type. The adapter validates its exact fields through the existing report
   schema and its method/unit registry before enqueueing. Do not serialize the
   receipt separately into general work-unit metrics or expose raw CLI output.
8. Emit one final usage event per run through the existing queue. Repeated
   delivery reuses the same event identity. Do not add progress usage events,
   aggregate parent/child runs or append a second event to revise a total.
   Corrections remain an existing, separate supersession operation. Reporting
   failure must not replace the launch outcome or erase the queued event.

## Changes

All companion paths below are relative to the companion checkout; all other
paths are relative to JEV Drill. These are the exact implementation boundaries.

### Companion `phase-loop-runtime/src/phase_loop_runtime/launcher.py` (modify)

- `LaunchResult`, `launch_with_spec`, `_result_with_spec` — add/preserve the optional
  normalized usage payload, explicit default-false capture kwarg, bounded version
  probe and private bounded JSONL collector. Preserve opaque web-search content,
  permanently invalidate rejected observations and qualify only adapter launches.
- `launch` and `_read_lines` — add stdout-only observation on the supervised Linux
  path, tagged stream handling and final drain for that optional capture path.
  Give reader EOF/error outcomes distinct tags and drain through both EOF tags.
  Preserve process cleanup, custody, stdin, deadlines and existing final-message
  completion proof. Do not parse the combined `LaunchResult.output` as telemetry.
- Keep existing executor identity metadata distinct from observed usage. A usage
  receipt establishes neither immutable model identity nor task acceptance.

### Companion `phase-loop-runtime/src/phase_loop_runtime/jevdrill_adapter.py` (modify)

- `prepare` — request JSONL for active Codex routing without changing prompt,
  selected model, effort, permission or hard-limit authority.
- `launch` — pass the private capture opt-in only for the bound Codex adapter
  launch, validate the receipt and replace only the four unknown token measurements
  when trustworthy values exist. Correct timeout/stall lifecycle classification
  while preserving interruption, selected/applied identity, host-monotonic timing,
  execution-run linkage and one-event queue semantics.
- `_validate_measurements` — register the explicit method and validate token
  integers/subsets at this boundary. Unsupported/malformed receipts produce
  unknown token measurements plus metadata-only diagnostics; they do not discard
  lifecycle events or change the executor result.

### Companion `phase-loop-runtime/tests/test_jevdrill_usage.py` (create)

- Parser fixtures and real local child-process stream controls: trusted stdout,
  forged stderr, nested tool content, malformed/duplicate keys, missing/zero
  categories, all-zero fallback, large counters, subsets, versions, repeated
  terminal events, child items, abrupt exit and late stdout drain. Require real
  duplicate-ID web-search positive records, duplicate-authoritative-key negatives,
  oversized/malformed collab followed by valid terminal usage, serialization-error
  substitutes, non-protocol stdout, read/decode failures, EOF-vs-error outcomes
  and model-reroute controls. Require the sequence thread.started -> turn.started
  -> announced lag/drop error item -> valid nonzero turn.completed to stay unknown.
  Permanent invalidation must survive later valid data; include the fifth native
  cache-write key in positive fixtures without creating a cache-write metric.
  Require graceful timeout and stall children that emit valid synthetic usage,
  handle SIGTERM and exit zero: preserve counters/identity, report failed lifecycle.
  Require a non-adapter --json control with no probe, merged stderr and no receipt,
  and probe-wrapper descendant cleanup with bounded timeout/pipe shutdown.
- Adapter-to-queue controls: immutable receipt propagation, unknown fallback,
  preserved completion/identity/authority and repeatable durable delivery.
  Use purpose-built local programs only; label all counters synthetic.

### Companion `phase-loop-runtime/tests/test_jevdrill_adapter.py` (modify)

- Extend the existing unknown-usage assertion with known and unsupported receipt
  cases; retain dry-run, recursion, operator override and requested-limit controls.
  Update existing launcher fakes/spec mocks for the optional capture kwarg and
  actual executor attribute; keep the original authority assertions intact.

### JEV `tests/conformance/test_usage_reporting.py` (create)

- Run the actual companion adapter in its separate interpreter, a controlled
  local Codex-shaped child, the installed JEV CLI and a new disposable queue/DB.
  Prove exact measurements survive queue restart, duplicate acknowledgment and
  SQLite replay. Persist no task/output/credential/reasoning sentinel.
- Prove missing, observably ambiguous and unsupported observations stay unknown.
  Failure without a valid terminal snapshot stays unknown; valid terminal usage
  followed by nonzero exit, timeout or stall retains counters with failed lifecycle
  and unchanged applied-identity semantics. Actual transport/storage execution is
  required; provider execution is false.

### JEV `scripts/verify_usage_reporting.py` (create)

- Collect the scoped Linux checks into a new private run directory. Build/install
  the current JEV wheel with locked dependencies in a separate environment using
  the existing release patterns; do not invoke the historical V0 prepare/live
  commands or reuse its environment/data. Pass the exact installed CLI path to
  conformance controls. Keep the companion interpreter separate.
- Record commands, input/schema/source/wheel digests, JUnit results, fixture
  telemetry provenance and redaction/delivery assertions in
  `evidence/USAGE-v0/verification.json`. Reduce acceptance only for this bounded
  change. Reject missing designated controls, failures or skips in those controls;
  record unrelated diagnostic skips without treating them as acceptance proof.
- Default execution uses no model/provider. Do not add a live flag or fallback.

### JEV `tests/verification/test_usage_reporting.py` (create)

- Test the scoped reducer against stale bindings, missing tests, skipped controls,
  raw-output leakage, unknown masquerading as zero, duplicate totals and missing
  durable replay. These controls must reject fabricated evidence.

### Documentation and registry (modify)

- Companion `docs/jevdrill-integration.md`: supported CLI/version, stdout
  provenance, snapshot semantics, accounting residuals, CLI-reported zero,
  launch-call timing scope, unknown cases and unchanged hard-limit rules.
- JEV `docs/host-interfaces.md`: the registered method, timing scope, CLI-zero
  semantics and residual accounting limits;
  distinguish fixture evidence from live provider or full HOST acceptance.
- JEV `docs/vocabulary.yaml`: add the host method as an external-identifier
  exception with explicit provenance; regenerate `docs/vocabulary.md` through
  the existing renderer. No new domain concept, module or BAML field is added.

Own only new evidence under `evidence/USAGE-v0/**` and operational outputs under
`.phase-loop/runs/USAGE-v0-20261001/**`. Preserve `evidence/V0/**`, all old pilot
and Gemma state, all roadmap gates and the investigation inputs.

## Dependencies & order

1. Reuse these assigned worktrees, compare saved starting statuses and read each
   owned file again before editing. Preserve inherited modifications, including
   those in launcher.py. Stop only for an actual overlapping edit conflict.
2. Add the stdout capture/receipt and its local controls, then adapter integration.
3. Add installed transport conformance and the scoped verification reducer.
4. Update method registration/docs; run targeted controls before broader checks.
5. Run the scoped suite, reduce its evidence and close out this plan only. Report
   later payload/cost work separately. No retrospective V0/full-roadmap closure.

## Verification

The companion root is supplied as `JEVDRILL_AGENT_HARNESS_ROOT`; the verifier must
require the path rather than silently substitute a global installed runtime.
The installed CLI is supplied to conformance via `JEVDRILL_TEST_CLI`. The companion
test runner uses `phase-loop-runtime/.venv/bin/python`; JEV uses `.venv/bin/python`.

Targeted commands, from their respective roots:

```sh
# Companion: new controls must run without skips or provider access.
phase-loop-runtime/.venv/bin/python -m pytest -q phase-loop-runtime/tests/test_jevdrill_usage.py phase-loop-runtime/tests/test_jevdrill_adapter.py phase-loop-runtime/tests/test_jevdrill_queue.py
# Companion: launcher lifecycle/custody regression checks.
phase-loop-runtime/.venv/bin/python -m pytest -q phase-loop-runtime/tests/test_launcher_liveness.py phase-loop-runtime/tests/test_launcher_exec_supervisor.py phase-loop-runtime/tests/test_phase_loop_launcher.py phase-loop-runtime/tests/test_executor_exited_without_closeout_785.py phase-loop-runtime/tests/test_launchspec_golden.py
# JEV: verifier/reducer controls, then installed conformance with explicit paths.
.venv/bin/python -m pytest -q tests/verification/test_usage_reporting.py
.venv/bin/python -m pytest -q tests/conformance/test_usage_reporting.py
.venv/bin/python scripts/render_vocabulary.py --check
.venv/bin/python scripts/lint_vocabulary.py
.venv/bin/python -m ruff check scripts/verify_usage_reporting.py tests/conformance/test_usage_reporting.py tests/verification/test_usage_reporting.py
.venv/bin/python -m ruff format --check scripts/verify_usage_reporting.py tests/conformance/test_usage_reporting.py tests/verification/test_usage_reporting.py
.venv/bin/python -m pytest -q
```

The five designated companion launcher suites above are required reducer controls:
launch_with_spec/_result_with_spec, completion proof/stdin and LaunchSpec guards
must run, not just liveness/supervision. The panel egress-prefix suite exercises
another subsystem and is not required for this change. New input/evidence metadata
records each pinned local source's upstream path without rewriting old inputs.

The scoped verifier sets isolated temp paths, removes provider-key variables from
children, prevents real executor invocation in fixtures, runs the commands above,
builds/installs the wheel, supplies installed conformance paths and collects
evidence. Inspect any broad-suite failure before retrying; do not weaken required
controls or assume older proof applies to changed inputs.

```sh
JEVDRILL_AGENT_HARNESS_ROOT=/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port .venv/bin/python scripts/verify_usage_reporting.py
```

automation.suite_command: JEVDRILL_AGENT_HARNESS_ROOT=/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port .venv/bin/python scripts/verify_usage_reporting.py

## Acceptance criteria

- [ ] Supported fresh-thread stdout counters survive LaunchResult propagation;
  stderr/tool output and unsupported/observably ambiguous cases stay unknown;
  announced drops stay permanently unknown, and ordinary non-adapter --json stays
  unchanged — proven by
  `test_jevdrill_usage.py` through the suite command.
- [ ] Cache/reasoning are subsets; missing differs from zero; all-zero upstream
  fallback is unknown; invalid integers/snapshots/streams stay permanently unknown,
  while genuine opaque web-search duplicate IDs stay supported —
  proven by designated parser controls through the suite command.
- [ ] One usage event retains selected/applied identity, permissions and requested
  limits; timeout/stall is failed even after graceful zero exit, and observed
  counters imply no completion claim, with no raw output or price/quality
  invention — proven by adapter and installed conformance controls through the
  suite command.
- [ ] Installed JEV CLI persistence, queue restart and duplicate delivery preserve
  exact counters once, while replay causes no executor/model invocation — proven
  by `tests/conformance/test_usage_reporting.py` through the suite command.
- [ ] Linux launcher drainage, timeout, cancellation and custody regressions pass;
  unknown capture cannot extend a launch deadline — proven by the designated
  subprocess controls and launcher regression commands through the suite command.
- [ ] The reducer binds fresh inputs, requires every designated control and rejects
  missing/stale/leaking evidence; required documentation/registry checks and JEV
  regressions pass — proven by `scripts/verify_usage_reporting.py` and its reducer
  tests. Evidence explicitly declares provider execution false and no full phase
  gate closure.

This is a standalone internal follow-up, not a claim to satisfy EC-HOST-1/2 or a
full cross-platform roadmap phase. Native macOS/Windows usage capture, app-server
adoption, provider-level call receipts, cache pricing, child/task totals and
cost/policy optimization remain outside this plan.
