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
It means a best-effort cumulative CLI observation for the supported fresh-thread
path, not a direct provider invoice or complete child-agent accounting.

## Behavior to implement

1. Capture only standard Linux Codex `exec` launches with native version
   `codex-cli 0.159.2`, a fresh thread and JSONL output. An active JEV adapter
   requests `json_output=True` before launch construction for Codex. Dry run,
   recursion bypass, other executors and launches without the adapter preserve
   their existing behavior. Unsupported versions still execute normally but
   yield unknown usage.
2. Probe the actual selected CLI with argv-based `--version`, timeout at most one
   second, without shell interpretation or inference. Perform the probe inside
   the existing timed launch, deduct its elapsed time from any execution deadline
   and never extend that deadline. A failed probe disables known usage, not the
   ordinary executor. If the deadline expires, use the existing unavailable or
   timeout behavior rather than dispatch outside it.
3. Observe stdout separately from stderr on the existing supervised Linux path.
   Pass an optional observer through ephemeral-monitor recursion and the
   supervisor path. Tag stream records, drain both streams after process exit
   before finalizing capture, and preserve combined output, log and heartbeat
   behavior. Bound reader shutdown; an incomplete stdout drain invalidates known
   usage. The existing unobserved/default path remains unchanged. Windows and
   other unsupported paths retain unknown usage.
4. Parse JSONL with duplicate-key rejection and a one-MiB per-record parsing
   limit. Accept only top-level protocol events from stdout. Ignore presentation
   text, nested tool output and unknown item content; never copy them into the
   receipt or report. Retain one terminal cumulative snapshot, never a sum of
   snapshots. Require one thread start, one turn start and one terminal completion
   with usage. Multiple starts, multiple terminal records, resume, compact/fork
   ambiguity, or observed collaboration/child-agent items invalidate known usage.
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
  normalized usage payload, version check and private bounded JSONL collector.
- `launch` and `_read_lines` — add stdout-only observation on the supervised Linux
  path, tagged stream handling and final drain for that optional capture path.
  Preserve process cleanup, custody, stdin, deadlines and existing final-message
  completion proof. Do not parse the combined `LaunchResult.output` as telemetry.
- Keep existing executor identity metadata distinct from observed usage. A usage
  receipt establishes neither immutable model identity nor task acceptance.

### Companion `phase-loop-runtime/src/phase_loop_runtime/jevdrill_adapter.py` (modify)

- `prepare` — request JSONL for active Codex routing without changing prompt,
  selected model, effort, permission or hard-limit authority.
- `launch` — validate the receipt and replace only the four unknown token
  measurements when trustworthy values exist; preserve host monotonic timing,
  lifecycle, execution-run linkage and one-event queue semantics.
- `_validate_measurements` — register the explicit method and validate token
  integers/subsets at this boundary. Unsupported/malformed receipts produce
  unknown token measurements plus metadata-only diagnostics; they do not discard
  lifecycle events or change the executor result.

### Companion `phase-loop-runtime/tests/test_jevdrill_usage.py` (create)

- Parser fixtures and real local child-process stream controls: trusted stdout,
  forged stderr, nested tool content, malformed/duplicate keys, missing/zero
  categories, all-zero fallback, large counters, subsets, versions, repeated
  terminal events, child items, abrupt exit and late stdout drain.
- Adapter-to-queue controls: immutable receipt propagation, unknown fallback,
  preserved completion/identity/authority and repeatable durable delivery.
  Use purpose-built local programs only; label all counters synthetic.

### Companion `phase-loop-runtime/tests/test_jevdrill_adapter.py` (modify)

- Extend the existing unknown-usage assertion with known and unsupported receipt
  cases; retain dry-run, recursion, operator override and requested-limit controls.

### JEV `tests/conformance/test_usage_reporting.py` (create)

- Run the actual companion adapter in its separate interpreter, a controlled
  local Codex-shaped child, the installed JEV CLI and a new disposable queue/DB.
  Prove exact measurements survive queue restart, duplicate acknowledgment and
  SQLite replay. Persist no task/output/credential/reasoning sentinel.
- Prove failed, missing, ambiguous and unsupported observations stay unknown.
  Actual transport/storage execution is required; provider execution is false.

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
  provenance, snapshot semantics, unknown cases and unchanged hard-limit rules.
- JEV `docs/host-interfaces.md`: the registered method and its scope/limits;
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
phase-loop-runtime/.venv/bin/python -m pytest -q phase-loop-runtime/tests/test_launcher_liveness.py phase-loop-runtime/tests/test_launcher_exec_supervisor.py
# JEV: verifier/reducer controls, then installed conformance with explicit paths.
.venv/bin/python -m pytest -q tests/verification/test_usage_reporting.py
.venv/bin/python -m pytest -q tests/conformance/test_usage_reporting.py
.venv/bin/python scripts/render_vocabulary.py --check
.venv/bin/python scripts/lint_vocabulary.py
.venv/bin/python -m ruff check scripts/verify_usage_reporting.py tests/conformance/test_usage_reporting.py tests/verification/test_usage_reporting.py
.venv/bin/python -m ruff format --check scripts/verify_usage_reporting.py tests/conformance/test_usage_reporting.py tests/verification/test_usage_reporting.py
.venv/bin/python -m pytest -q
```

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
  stderr/tool output and unsupported/ambiguous cases stay unknown — proven by
  `test_jevdrill_usage.py` through the suite command.
- [ ] Cache/reasoning are subsets; missing differs from zero; all-zero upstream
  fallback is unknown; invalid integers/snapshots cannot become known usage —
  proven by designated parser controls through the suite command.
- [ ] One usage event retains existing lifecycle, selected/applied identity,
  permissions and requested-limit behavior, with no raw output or price/quality
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
