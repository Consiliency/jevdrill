# Correctness re-review: observed Codex usage plan (round 2, bound delta)

**Artifact under review:** `plans/detailed-usage-reporting-20261001-1610.md` (sha256 `e77c9182…cdd4`), reviewed as the bound delta from the round-1 plan (`baf70220…5899`).

**Lens:** correctness. I reviewed by reading source only. I ran no builds, tests, providers or CLIs, accessed no credentials, and edited nothing except this file. Nothing in this review claims that a test passed.

## Input binding

- **Bundle and inputs.** The bundle sha256 `2b5afac3…1c11` matches. All 17 referenced files match their bundle digests on the current working bytes.
- **Delta.** The base digest in `delta-binding.json` equals the round-1 plan I reviewed. Running `diff -u` from base to head reproduces the body of `round2/delta.diff` exactly.
- **New pin.** `research/usage-review/upstream/exec-lib.rs` is `openai/codex` `codex-rs/exec/src/lib.rs` at `ff6aec96…`, the plan's input commit. Its digest agrees across the plan text (lines 47–49), `upstream/inputs.json` and the bundle.

## Round-1 findings: resolution

### C-1: resolved by A2

- **Plan text.** Behavior 4 (lines 136–146), the fixture list (224–228) and AC2 (349–352).
- **The strictness scope accepts every genuine record.**
  - `ThreadItem` is an `id` plus `type`-tagged details flattened into the same object (exec-contract.rs:96–107).
  - No variant struct declares a field named `type` (138–324), so `item.type` is always unique. Only `WebSearchItem` repeats `id` (298–299).
- **The serialization-error substitute is detectable inside the strict scope.** It is a well-formed top-level `error` event with the fixed prefix `failed to serialize exec json event:` (exec-events.rs:105–116). Detecting it reads only the event envelope.
- **The new "every nonempty stdout line must be protocol" rule does not fail closed on the supported path.**
  - exec-lib.rs:1–6 requires JSONL-only stdout in `--json` mode and denies `print_stdout`.
  - The JSON emitter's `print_final_output` only writes the last-message file (exec-events.rs:631–637).
  - The lease supervisor reports its handshake on a private status fd (lease_supervisor.py:12–23). After the fork it closes its own stdio (397). Its only standard-stream write is a usage error to stderr (433).

### C-2: resolved by A4

- **Plan text.** Behavior 1 (105–114), the adapter changes (209–213), the non-adapter control (231) and AC1 (347).
- **The kwarg reaches the real launcher.**
  - All three runner adapter sites pass `launch_with_spec` itself into `launch_jevdrill` (runner.py:4714, 5381, 6039).
  - `launch_jevdrill` forwards it to `JevDrillAdapter.launch` (jevdrill_adapter.py:521–522), which calls it with `**kwargs` (437–458).
  - The unbound branch (440) passes no opt-in, so the default of false applies.
- **No JEV test breaks.** The `launch_with_spec` monkeypatch in JEV's `test_bridge_probe.py` lies outside JEV `testpaths` (pyproject.toml:30).

### C-3: resolved by A1, with one gap (R2-1)

- **Plan text.** Lines 94–101 and 150–152, and the docs section (276–281). "Compact" is gone from the invalidator list, compaction is stated as a non-guarantee, and the residuals are named.
- **The new attribution claim holds.** Exec submits exactly one `UserTurn` (exec-lib.rs:1134–1188). It forwards only notifications for the root thread and that turn, including token updates (1280–1284, 1636–1638).
- **Treating compaction as a residual is consistent.** The pinned sources contain no stdout signal for compaction. The only trace is `ContextCompacted` (protocol.rs:1399–1400), which exec does not map.

### C-4: resolved by A5

- **Plan text.** Lines 314 and 325–329.
- **All five suites exist under `phase-loop-runtime/tests/`.**
  - `test_phase_loop_launcher.py` calls `launch_with_spec` 9 times.
  - `test_executor_exited_without_closeout_785.py:175–195` drives a real Codex-shaped child through stdin and the `--output-last-message` completion proof. The child handles SIGTERM by exiting 0 (191).

### Other amendments

- **A3 (ADV-01) is sound.**
  - `LaunchResult.failed` checks only the return code (launcher.py:350–352). `timed_out` and `stalled` are separate fields (320–322), and adapter:459 ignores them.
  - `LifecyclePayload` has no timeout event type (contracts.baml:76), so `failed` is the correct mapping.
  - On the supervised path, the supervisor forwards SIGTERM and the child's return code propagates (lease_supervisor.py:377–393), so the graceful zero-exit case can actually occur.
  - No existing adapter assertion expects `completed` for a timed-out or stalled result. The identity rule matches adapter:462.
- **Forcing `--json` does not disturb completion or closeout.** Codex closeout comes from `--output-last-message` (launcher.py:2150, 2170–2182, 2494–2497). The JSON emitter still writes that file for completed turns.
- **The N-3 rewording is accurate.** The Linux ephemeral monitor uses a local temporary log and does not recurse (launcher.py:2791–2794).
- **Deferred items.** The dispositions for C-5 through C-9 and N-1 through N-2 are acceptable.

## Remaining finding

### R2-1 (Medium; BLOCKING; fails toward known data)

**Breaks:** AC1, Behavior 4's child-agent rule, and reconciliation A1's "reject observable ambiguity".

**Issue:** Behavior 4 does not reject the pinned in-process *lag* notice. Codex writes that notice to stdout to say it dropped item notifications.

**Where:** Plan §Behavior 4 invalidator list (lines 147–152), the residual list (96–99), the `test_jevdrill_usage.py` fixtures (221–232) and AC1 (345–348).

**Evidence** (pinned 0.159.2 sources; `exec-lib.rs` is this delta's own new pin):

- **Items can be dropped.** In-process delivery uses a bounded channel (exec-lib.rs:18, 732). Upstream states: "In-process delivery may drop non-terminal item notifications under backpressure while still guaranteeing `turn/completed`" (1661–1664).
- **The drop is announced on stdout.**
  - A drop surfaces as `InProcessServerEvent::Lagged`, which calls `process_warning("in-process app-server event stream lagged; dropped {skipped} events")` (1310–1313, 1587–1589).
  - The warning is written to stdout as an `item.completed` record with `item.type == "error"` (exec-events.rs:409–419, 623–629).
  - This is the same pinned mechanism as the model-rerouted notice, which the plan already rejects (494–507).
- **Backfill does not restore dropped items.**
  - `reconcile_unfinished_started_items` emits only items whose start was observed (exec-events.rs:370–385; driven from exec-lib.rs:1285–1291, 1700–1709).
  - A `collab_tool_call` whose start and completion were both dropped therefore never reaches stdout.
  - Root totals exclude child threads by construction (exec-lib.rs:1636–1638). The collab item is the only stdout evidence Behavior 4 has for the child-agent rule.

**What breaks:**

- **A concealed run passes as known.** The sequence `thread.started → turn.started → lag notice → valid nonzero turn.completed` passes every listed check and becomes durable known `scope="run"` usage. Yet the stream has said that the child-agent evidence is incomplete.
  - The president ruled this class of AC1 concealment BLOCKING in ADV-03. There the collab record was oversized; here it was dropped.
- **The listed residual does not cover it.** The "dropped internal notifications" residual on line 98 comes from C-3: exec's silent filtering of unmapped notifications (exec-events.rs:323, 598), which stdout cannot see. A drop that exec announces is observable, so A1 and AC1 require unknown.
- **It cannot be fixed after the fact.** Receipts and reports keep no raw stdout, so affected records cannot later be identified or superseded. Capture time is the only point where they can be rejected.

**Smallest repair:**

1. Add the pinned lag notice to Behavior 4's invalidators: an `error` item whose `message` starts with `in-process app-server event stream lagged; dropped `.
2. State that matching the two pinned notices reads only the string `item.message` of `error` items. All other item content stays opaque.
3. Add this negative control to the designated parser controls: `thread.started → turn.started → lag notice → valid nonzero turn.completed` stays unknown, permanently, even when valid data follows.
4. In both integration docs, split the residual: announced drops are rejected, and unannounced exec filtering stays uncertified.

No contract, wire or scope change is needed.

## Non-blocking notes

- **N-a (real usage shape).** Genuine 0.159.2 `usage` has five keys. The fifth is `cache_write_input_tokens` (`#[serde(default)]`, exec-contract.rs:66–68; populated at exec-events.rs:125).
  - Positive fixtures should use this real shape.
  - The collector should accept the key without mapping it, consistent with line 160.
  - Otherwise a strict key check could pass four-key synthetic fixtures while rejecting every real run.
- **N-b (adapter test compatibility).** Existing adapter controls use `SimpleNamespace` specs that have no `executor` attribute, and one fake launcher accepts positional arguments only: `def execute(*args)` (test_jevdrill_adapter.py:196–202). Gate the opt-in on a guarded executor check so those retained controls keep working.
- **N-c (stderr decoding).** The streaming Popen decodes strictly (`text=True`, launcher.py:2854).
  - Under the rule that both streams must reach a clean EOF, a stderr-only decode error invalidates usage.
  - It also stops stderr draining; the merged path already has that hazard.
  - The failure mode is unknown, which is safe. Optionally, invalidate only on stdout reader outcomes.

## Unverified assumptions

- **Which notifications can be dropped.** The drop policy and channel capacity live in the unpinned in-process client. If `ThreadTokenUsageUpdated` can also be dropped, R2-1 additionally produces stale, undercounted root totals.
- **Whether collab tools are active.** I did not establish whether collab or multi-agent tools are enabled on 0.159.2 non-review launches under default or user config. This affects how often R2-1 occurs, not whether it is valid.
- **Fidelity of the pinned copies.** I checked digests against `rust-v0.159.2` only; I did no network fetch.
- **The npm wrapper.** I assume the npm `codex` wrapper writes nothing to stdout. It is unpinned; if it did, the result would fail closed to unknown.
- **SIGTERM handling.** Pinned exec-lib handles only Ctrl-C (exec-lib.rs:1128), so real Codex likely dies by signal on SIGTERM, and A3 mainly governs graceful children. I did not check unpinned crates.
- **Suite status.** I did not run the designated suites, and I have not verified that the inherited companion tree passes them.

## Inspected paths

**JEV:**

- `plans/detailed-usage-reporting-20261001-1610.md`
- `research/usage-review/`:
  - `reconciliation.md`
  - `round2/`: `delta.diff`, `delta-binding.json`, `review-instructions.md`
  - `round1/`: `reviewed-plan.md`, `claude/verdict.md`, `president/ruling-2.md`
  - `upstream/`: `exec-lib.rs`, `inputs.json`
- `.phase-loop/runs/PLAN-usage-reporting-20261001-1610/`: `exec-events.rs`, `exec-contract.rs`, `protocol.rs`
- `research/runtime-accounting/observations-20261001.json`
- `baml_src/contracts.baml`
- `pyproject.toml`
- `research/evaluation/host/test_bridge_probe.py`

**Companion (`phase-loop-runtime/`):**

- `src/phase_loop_runtime/`: `launcher.py`, `jevdrill_adapter.py`, `lease_supervisor.py`, `runner.py`
- `tests/`: `test_jevdrill_adapter.py`, `test_executor_exited_without_closeout_785.py`, `test_phase_loop_launcher.py`, `test_launchspec_golden.py`, `test_launcher_liveness.py`, `test_launcher_exec_supervisor.py`

**Digest-checked only.** The delta changes none of their contracts, so my round-1 conclusions carry:

- `research/runtime-accounting/investigation-20261001.md`
- `schemas/ReportRequest.json`
- `src/jevdrill/application.py` and `src/jevdrill/storage.py`
- `docs/host-interfaces.md`
- `jevdrill_queue.py`

## Verdict rationale

Checked against current source, the delta resolves all four of my round-1 required amendments (C-1 to C-4). It also correctly adds the A3 lifecycle fix and the A4 opt-in. The new exec-lib pin confirms root-thread attribution.

One narrow blocker remains. The plan's own rule is to reject observable ambiguity, but it omits the one pinned stdout signal that says child-agent evidence was dropped. Under AC1, such a run can become durable known usage that cannot be identified or corrected later. The repair is one invalidator and one control. Once that change is in the plan, I expect to agree.

DISAGREE
