# Correctness review: observed Codex usage plan (round 1)

**Artifact under review:** `plans/detailed-usage-reporting-20261001-1610.md` (sha256 `baf70220…5899`).

**Lens:** correctness. I reviewed by reading source only. I did not run builds, tests, providers or CLIs, and I did not access any credentials. Nothing in this review claims that a test passed.

## Input binding

- **Bundle and inputs.** The bundle sha256 `7cfaeee9…cdeb` matches. All 13 referenced files match their bundle digests on the current working bytes. Every `inputs.json` digest also matches, including `protocol.rs` and `schemas/ReportAcknowledgment.json`.
- **HEADs.** JEV HEAD `77d41b2c…` and companion HEAD `56dce95a…` equal the plan's recorded inputs.
- **Inherited work.** In the companion, `jevdrill_adapter.py`, `jevdrill_queue.py` and `docs/jevdrill-integration.md` are untracked inherited work, and `launcher.py` carries inherited modifications. I reviewed the working bytes, not HEAD.
- **Schema fixtures.** All 8 companion `tests/fixtures/jevdrill/*.json` schemas are byte-identical to JEV's current `schemas/*.json`, so there is no wire drift.

## Verified sound (source inspection)

- **Result seam.** `LaunchResult` is a frozen dataclass. `_result_with_spec` (launcher.py:3880–3929) rebuilds it field by field, so a new `jevdrill_usage` must be copied explicitly, which the plan says.
- **Stream handling and custody.**
  - The streaming path merges stderr at the OS level (launcher.py:2857).
  - After process exit, the drain uses `get_nowait()` and then `reader.join(timeout=1)` (2963–2981). Late lines can be lost today, so the plan's "tag streams, drain before finalizing" design targets a real race.
  - The lease supervisor keeps fds 0/1/2 for the executor (lease_supervisor.py:298) and resolves the binary with `execvpe` using the received environment (:317). Stdout separation therefore survives custody.
- **Upstream semantics.**
  - `usage_from_last_total` returns `Usage::default()` when no update arrived, and otherwise the latest `total` (exec-events.rs:118–129, 509–512, 533–535). "Never sum; all-zero is ambiguous" follows directly.
  - Upstream arithmetic treats cached ⊆ input and reasoning ⊆ output (protocol.rs:2430–2437, 2494–2514).
- **Contract.** `Measurement.method` is a free string, and `source:"host"`, `scope:"run"` and subset semantics are all permitted. JEV only enforces that a subset has a parent (contracts.py:127). `redact()` matches credential patterns only. Storage keeps integers exact and deduplicates by event id and digest (storage.py:913–994). No wire change is needed.
- **Fresh thread.** A fresh thread is structural: `build_codex_command` never emits `resume` (launcher.py:596–634).
- **Existing conformance.** Existing JEV HOST conformance is not disturbed. `test_bridge_probe.py` monkeypatches `launch_with_spec`. `test_baseline_probe.py` hardcodes unknown usage and never inspects `spec.command`.
- **Fixture isolation.** `child_executor_env` preserves `PATH`, so isolating a fixture binary through `PATH` is feasible.
- **Consumers.** No JEV consumer keys token metrics on `source=="provider"`.

## Findings

**Blocking:** none. C-1 through C-4 are required plan amendments for the bound delta. C-5 through C-9 and the nits are suggestions.

### C-1 (High; required amendment; fails toward unknown, so not data-corrupting)

**Issue:** The duplicate-key rule conflicts with real 0.159.2 `web_search` records, and the plan does not define what happens to a record that fails parsing.

**Where:** Plan §Behavior 4 ("Parse JSONL with duplicate-key rejection…") and the `test_jevdrill_usage.py` fixture list ("malformed/duplicate keys").

**Evidence:**
- The pinned upstream `exec_events.rs` copy (`exec-contract.rs:97–102`) declares `ThreadItem { id, #[serde(flatten)] details }`, and `WebSearchItem` has its own `id` field (`:297–306`).
- `exec-events.rs:303–306` populates both ids.
- serde does not deduplicate keys emitted through `flatten`. So every `item.started` and `item.completed` web-search record carries two `"id"` keys inside `item`. This is by inspection; I did not execute it.
- Non-review launches load user config, because `--ignore-user-config` appears only on the read-only path (launcher.py:620–622). Web search is therefore not excluded.

**What breaks:**
- *Fail-closed reading* (the one the fixture list implies): every supported run that performs a web search reports unknown usage, while the synthetic fixtures still pass. This breaks AC1 ("supported fresh-thread stdout counters survive").
- *Skip-the-record reading*: a malformed or over-1-MiB `collab_tool_call` record would be silently ignored. That bypasses child-agent invalidation and breaks AC1 ("ambiguous cases stay unknown").

**Smallest repair:**
- Apply strict duplicate-key and number checks only to the top-level event object, `usage`, and `item.type`. Treat the rest of `item` as opaque.
- State that any `{`-prefixed stdout record that is malformed, oversized, or has an unclassifiable `type`/`item.type` invalidates known usage.
- Add a positive fixture using the real duplicate-`id` web_search shape.
- Add a negative fixture with an unparseable collab record.

### C-2 (Medium–High; required amendment)

**Issue:** The plan defines no explicit opt-in from the adapter to the launcher, and an argv `--json` flag does not identify adapter launches.

**Where:** Plan §Behavior 1 and 3, and §Changes (launcher `launch_with_spec`, adapter `launch`).

**Evidence:**
- The operator's `--json` already reaches Codex as `--json` with no adapter involved: cli.py:1879 passes `json_output=as_json` into `build_launch_request`, which emits `--json` at launcher.py:627–628.
- The plan names no channel through which `launch_with_spec` learns that the adapter requested capture.

**What breaks:** Behavior #1 ("launches without the adapter preserve their existing behavior") and #3 ("the existing unobserved/default path remains unchanged"). An implementation gated on argv would add a probe subprocess and split pipes to ordinary operator `--json` runs. No designated control covers this case.

**Smallest repair:**
- Have `JevDrillAdapter.launch` pass an explicit private kwarg, for example `codex_usage_capture=True`, to `launch_with_spec`.
- Capture only when that kwarg is set, the executor is `codex`, and the platform is Linux.
- Add a control proving that a non-adapter `--json` Codex launch runs no probe, keeps `stderr=STDOUT`, and returns `jevdrill_usage is None`.

### C-3 (Medium; required amendment)

**Issue:** The rule "compact/fork ambiguity … invalidates known usage" cannot be implemented from 0.159.2 stdout, and the residual gaps are not documented.

**Where:** Plan §Behavior 4 and §Documentation and registry.

**Evidence:**
- Exec drops unmapped items (`exec-events.rs:323`, `_ => None`) and unmapped notifications (`:598`). The exec event enum has no compaction variant, so compaction never appears on stdout.
- The collab tools SendMessage, FollowupTask, InterruptAgent and ListAgents, and the Interrupted collab status, are suppressed (`:248–251`, `:299`).
- `protocol.rs` defines `SubAgentSource::Compact` (2910), memory-consolidation and guardian sources, and `fill_to_context_window`, which resets cumulative categories (2316–2329).
- `ThreadTokenUsageUpdated` is stored without checking its thread (`exec-events.rs:509–512`). Any filtering happens in exec code that is not pinned.

**What breaks:** AC1's claim that ambiguous cases stay unknown. Long phase runs can auto-compact. The resulting `scope:"run"` value may then omit compaction or internal sub-agent usage while the docs claim those cases are unknown.

**Smallest repair:**
- Remove "compact" from the invalidation list. Keep resume and fork as an exclusion that is structural in argv.
- In both docs, list compaction, internal sub-agents (review, compact, memory, guardian), provider retries and mid-thread total resets as residuals of `codex_exec_jsonl_0_159_2_v1`.
- Optionally, pin `codex-rs/exec/src/lib.rs` to establish that exec filters notifications to the root thread.

### C-4 (Medium; required amendment; verification gap)

**Issue:** The AC5 regression set omits the suite that exercises the modified seam.

**Where:** Plan §Verification, in the companion launcher regression command.

**Evidence:**
- `tests/test_phase_loop_launcher.py` calls `launch_with_spec` 9 times.
- The two listed suites, `test_launcher_liveness.py` and `test_launcher_exec_supervisor.py`, reference neither `launch_with_spec` nor `_result_with_spec`.
- The full JEV `pytest` run does not include companion tests.

**What breaks:** AC5's proof does not exercise the functions the plan modifies.

**Smallest repair:** Add `test_phase_loop_launcher.py`, `test_launchspec_golden.py` and `test_the_real_launch_carries_the_prefix.py` to the designated launcher command and to the reducer's list of required controls.

### C-5 (Medium; suggestion; unverified assumption)

**Issue:** Treating a zero subcategory as "known zero" relies on an upstream mapping and a provider that the plan has not pinned.

**Where:** Plan §Behavior 5 ("zero categories … remain known zero") and AC2 ("missing differs from zero").

**Evidence:**
- The subcategory fields in `TokenUsage` and in exec `Usage` are non-optional `i64` (protocol.rs:2241–2254; exec-contract.rs:61–73). The stdout boundary therefore cannot express "missing".
- Whether absent provider detail fields default to 0 is decided in client code that is not pinned.
- User config can select a non-OpenAI `model_provider` on non-review launches.

**Repair:** Document that subcategory zeros mean "as reported by the CLI" and are verified only for the OpenAI Responses path. Alternatively, emit known tokens only when the bound candidate's `provider` is the verified one.

### C-6 (Low–Medium; suggestion)

**Issue:** The version probe runs inside the adapter's timed window.

**Evidence:**
- The adapter times the entire `launch(spec)` call (jevdrill_adapter.py:456, 471). Plan §Behavior 2 puts the probe inside that call.
- The companion doc publishes "Actual elapsed execution time is measured with the host monotonic clock" (docs/jevdrill-integration.md:101–102).
- A probe of up to 1 s on adapter-routed Codex runs alone skews cross-executor `completion_time_ms`. This is mitigated by `launch()` already including git-snapshot overhead.

**Repair:** Cache the probe result per resolved executable identity, or return the probe's elapsed time so the adapter can subtract it.

### C-7 (Low; suggestion)

**Issue:** The probe and the launch can resolve different binaries, and the probe child may outlive a timeout.

**Evidence:** `command[0]` is the bare name `codex` (launcher.py:597), resolved at spawn time by `Popen` or `execvpe`.

**Repair:**
- Resolve `codex` once against the `child_env` `PATH`, probe that absolute path, and substitute it into the launched argv on both the direct and supervisor paths.
- Run the probe in its own session and kill its process group on timeout, because the npm wrapper spawns a native child.
- Note that `--json` is requested before the version is known. "Unsupported versions still execute normally" therefore assumes those versions accept `--json`.

### C-8 (Low; suggestion)

**Issue:** Model reroutes that are visible on stdout are ignored.

**Evidence:**
- `ModelRerouted` is emitted as an `error` item with the message "model rerouted: X -> Y" (exec-events.rs:494–507).
- `_result_with_spec` overwrites `selected_model` from the spec, so the adapter's mismatch check (jevdrill_adapter.py:460–462) cannot detect a reroute.
- Known tokens would then be attributed to the selected plan's conditions (storage.py:551–565).

**Repair:** Treat this version-pinned notice as ambiguity, which makes the tokens unknown, and add a fixture for it.

### C-9 (Low; suggestion)

**Issue:** Forcing `--json` changes the runner's failure classifier.

**Evidence:**
- Failed launches are classified by substring matching over `result.output` (runner.py:3665, 11019–11034).
- The markers include `"usage"`, and every JSONL `turn.completed` record contains that string.
- A JSON-mode Codex run that exits nonzero after completing its turn, without a timeout or stall, would be classified `account_or_billing_setup` instead of `unknown`.

**Repair:** Add a regression control, or exclude parsed protocol records from the classifier's input.

### Nits

- **N-1:** The pinned-copy names are inverted relative to upstream. `exec-events.rs` holds `event_processor_with_jsonl_output.rs`, and `exec-contract.rs` holds `exec_events.rs`. Record an `upstream_path` for each entry in `inputs.json`.
- **N-2:** All unknown cases map to `not_reported`. Using `unsupported` for version or platform gaps and `incomplete` for drain failures or failed runs would keep more meaning within the existing enum.
- **N-3:** On Linux, the only launcher recursion is the lease-supervisor path. Ephemeral-monitor recursion happens only on Windows (launcher.py:2742–2750).

## Unverified assumptions

- The pinned `.rs` copies faithfully match `rust-v0.159.2` / `ff6aec96…`. I checked digests only and did no network fetch.
- Exec filters notifications to the root thread (see C-3).
- `codex --version` prints exactly `codex-cli 0.159.2` within 1 s on the target host.
- The inherited companion working tree currently passes the named regression suites. I did not run them.
- Under `--json`, Codex writes only JSONL to stdout and sends tracing to stderr.
- **Trust boundary.** Under `danger-full-access`, executor tools act with the user's authority and can write to a dumpable ancestor's stdout through `/proc`. Stdout separation guards against channel confusion, not against a hostile executor. Combined with "a valid snapshot may survive later failure", a tool could inject a terminal record and then kill the process. Optionally, require `codex_turn_completion.completed` before recording known usage.

## Inspected paths

**JEV:**
- `plans/detailed-usage-reporting-20261001-1610.md`
- `research/runtime-accounting/investigation-20261001.md` and `observations-20261001.json`
- `.phase-loop/runs/PLAN-usage-reporting-20261001-1610/`: `exec-events.rs`, `exec-contract.rs`, `protocol.rs`, `inputs.json`, `closeout.json`, `status-comparison.json`
- `baml_src/contracts.baml`
- `schemas/ReportRequest.json`, `schemas/ReportAcknowledgment.json`
- `src/jevdrill/`: `application.py`, `storage.py`, `contracts.py`, `context.py`, `evaluation.py`, `analysis.py`
- `docs/host-interfaces.md`, `docs/vocabulary.yaml`
- `scripts/`: `lint_vocabulary.py`, `verify_host_phase.py`, `verify_v0_release.py`
- `tests/conformance/`: `conftest.py`, `test_transport_queue.py`
- `research/evaluation/host/`: `test_bridge_probe.py`, `test_baseline_probe.py`

**Companion (`phase-loop-runtime/`):**
- `src/phase_loop_runtime/`: `launcher.py`, `jevdrill_adapter.py`, `jevdrill_queue.py`, `lease_supervisor.py`, `harness_env_signatures.py`, `runner.py`, `cli.py`
- `tests/`: `test_jevdrill_adapter.py`, `test_phase_loop_launcher.py`
- `tests/fixtures/jevdrill/*`
- `docs/jevdrill-integration.md` (at the companion repo root)

## Verdict rationale

The architecture is sound and grounded in current source. The seam, the reuse of existing contracts, the queue and deduplication semantics, the privacy boundary and the no-wire-change claim all hold against the current bytes.

No finding causes genuine Codex output to be recorded as corrupted known data, and none causes a privacy breach. Under the review definition, nothing is blocking. However, C-1 through C-4 should be amended in the bound delta before execution. Each is an ambiguity or proof gap against the pinned 0.159.2 source or the existing launcher seam, and each has a small repair.

PARTIALLY AGREE
