# Correctness re-review: observed Codex usage plan (round 3, final, bound delta)

**Artifact under review:** `plans/detailed-usage-reporting-20261001-1610.md` (sha256 `0727eabd…9d58`), reviewed as the bound delta from the round-2 plan (`e77c9182…cdd4`).

**Lens:** correctness. I reviewed by reading source only. I ran no builds, tests, providers or CLIs, accessed no credentials, and edited nothing except this file. Nothing in this review claims that a test passed.

## Input binding

- **Bundle.** sha256 `48ff2657…3eb7` (5779 bytes) matches. All 19 referenced files match their bundle digests on the current working bytes.
- **Delta.** `delta-binding.json` names the round-2 reviewed plan (`e77c9182…cdd4`) as base, and that file has that digest. Running `diff -u` from base to head reproduces the body of `round3/delta.diff` exactly. `carry-forward.json` binds the same head (`0727eabd…`).
- **Runtime sources unchanged.** Every runtime and pinned-source digest in this bundle equals the round-2 bundle:
  - Companion: `launcher.py`, `jevdrill_adapter.py`, `jevdrill_queue.py`.
  - Pinned upstream: `exec-events.rs`, `exec-contract.rs`, `exec-lib.rs`.
  - JEV: `contracts.baml`, `ReportRequest.json`, `application.py`, `storage.py`, `host-interfaces.md`.
  - This corroborates `runtime_source_changes: false`. Only the plan and the review records changed.

## R2-1: resolved

R2-1 found that Behavior 4 accepted a run after Codex announced on stdout that it had dropped item notifications. I proposed a four-step repair; the delta implements all four, and each checks out against the pinned 0.159.2 sources.

### Step 1: the lag invalidator (plan 154–157)

- **The prefix is exact.** `in-process app-server event stream lagged; dropped ` is the literal start of `lagged_event_warning_message` (exec-lib.rs:1587–1588).
- **The message reaches stdout unchanged.**
  - The `Lagged` arm passes it to `process_warning` (exec-lib.rs:1310–1313).
  - `process_warning` calls `collect_warning`, which emits it unmodified as `item.completed` with an `error` item (exec-events.rs:409–419, 623–629).
  - `model rerouted: ` is likewise the literal start of exec-events.rs:500.
- **Coverage is complete within the pinned scope.**
  - `client.next_event()` has a single consumer (exec-lib.rs:1248), so every in-process `Lagged` reaches the notice.
  - No other lag, drop or backpressure text exists in any pinned source (exec-lib, exec-events, exec-contract, protocol).
  - In JSON mode the only other `process_warning` caller, the bwrap warning, is suppressed by `!json_mode` (exec-lib.rs:1117–1122).
- **Position cannot defeat it.**
  - `thread.started` is emitted before the event loop (exec-lib.rs:1116; exec-events.rs:606–612).
  - A completed turn returns `InitiateShutdown` immediately after emitting `turn.completed` (exec-events.rs:526–537), and the loop breaks (exec-lib.rs:1295–1306).
  - The notice can therefore only appear before the terminal record, and the permanent, order-independent invalidator covers every position.

### Step 2: the inspection scope is narrow and safe (plan 154–159)

- **Genuine error items always pass the new strictness.**
  - A genuine `error` item has exactly `{id, type, message}`: `ThreadItem` is `id` plus internally tagged details flattened into the same object (exec-contract.rs:96–107).
  - `ErrorItem`'s only field is `message: String` (310–312), so a genuine record always has one string `message`.
  - Consequently, "Duplicate/malformed message discriminators are invalid" cannot reject a genuine record.
- **Nested content stays opaque.** Nested `message` fields inside collab or MCP content (exec-contract.rs:245–248, 280–282) are not inspected. The web_search opacity that the carried seats relied on is untouched.
- **The exception cannot cause acceptance.** It can only reject a run, and it copies nothing into receipts.
  - This is consistent with A2's opacity rule.
  - The ruling's C-8 hardening already required this one read, because detecting the reroute notice means reading that message.
- **Common warnings still pass.** ConfigWarning and DeprecationNotice items are always processed (exec-lib.rs:1597), and server Warnings are processed when unscoped or root-scoped (1599–1602). All become error items (exec-events.rs:427–473), and they stay accepted unless their message starts with a pinned prefix.

### Step 3: the negative control (plan 237–239)

- The required sequence is `thread.started → turn.started → lag notice → valid nonzero turn.completed`. It must stay unknown, and permanent invalidation must survive later valid data (239).
- AC1 (359–363) now names announced drops as permanently unknown.

### Step 4: the residual split (plan 97–101)

- "Unannounced internal notification filtering" now names exec's silent drops of unmapped items and notifications (exec-events.rs:323, 598; exec-lib.rs:1651).
- Announced drops now invalidate capture.
- Both integration documents must state the distinction (doc bullets 290–295).

### Effect

The concealment path in R2-1 is closed for every drop that pinned exec announces: a dropped collab item can no longer let a run become durable known usage. The delta only adds rejection conditions and test obligations. It changes no contract, wire format or scope. The three carried AGREE seats are therefore not undermined.

## Round-2 non-blocking notes

- **N-a: resolved** (plan 142–143, 239–240).
  - Pinned `Usage` always serializes five `i64` fields: `#[serde(default)]` applies only when reading, and there is no `skip_serializing_if` (exec-contract.rs:60–73). The fifth field is populated at exec-events.rs:125.
  - The installed 0.159.2 schema probe also lists `cacheWriteInputTokens` (`observations-20261001.json`, `native_schema_probe`).
  - Number strictness still applies to the fifth key. No subset rule is imposed on it, and Behavior 5 (169) still forbids a cache-write metric.
- **N-b: resolved by a different, acceptable route** (plan 253–254). The plan updates the fakes and mocks rather than guarding the executor read.
  - A grep of the companion `tests/` finds no adapter-launch fakes outside `test_jevdrill_adapter.py`, which is inside the change boundary.
  - That update covers the positional-only fake `def execute(*args)` (196–202) and the `SimpleNamespace` specs without `executor` (123, 172, 196, 288, 338, 484, 501, 522).
  - The runner-driven `controlled_executor(spec, **kwargs)` (377) already accepts the kwarg, and the real `LaunchSpec` has `executor: str` (launcher.py:176–177).
  - The dry-run and recursion pass-through equality assertions (183, 185) still hold, because `prepare` returns before it routes (jevdrill_adapter.py:300–308).
  - An equivalent alternative: `prepare` already reads `kwargs["executor"]` (324) and could record it in the binding.
- **N-c: unchanged, still optional.** Strict text decoding remains at launcher.py:2854. The failure mode is unknown usage, which is safe.

## Remaining findings

**No blocking findings.** The following suggestions are optional and are not required before implementation:

- **S-1 (Low; AC1 test completeness).** Add a positive control: a non-matching genuine error item (deprecation or config-warning shape), followed by valid nonzero five-key usage, stays known.
  - This pins how narrow the exception is.
  - An over-broad "any error item invalidates" implementation would pass every listed control. It would still fail safe to unknown, but it would lose counters on supported runs, contrary to AC1's survival clause.
- **S-2 (Low).** Make the JEV conformance child (plan 258) emit the genuine five-key shape. Behavior 4's "positive fixtures" wording already implies this.
- **S-3 (Low; record hygiene).** `reconciliation.md` is unchanged since round 2. It still says "Round 2 reviews the bound delta", and its A1 row lists "dropped notifications" as uncertified. Record the R2-1 split there so the review record matches plan 97–101; the plan governs.

## Unverified assumptions

- **Unannounced in-process drops.** I assume the unpinned in-process client reports every drop as `Lagged`. The upstream comment (exec-lib.rs:1661–1664) and the event shape imply this, but I did not inspect the client crate. Any silent client-side drop would fall under the documented unannounced residual.
- **Collab tool enablement.** I did not establish whether collab or multi-agent tools are enabled on default 0.159.2 launches. This affects how often the lag invalidator fires, not whether it is correct.
- **Pinned copy fidelity.** I checked digests only against the recorded provenance; I did no network fetch.
- **The npm wrapper.** I assume the `codex` npm wrapper writes nothing to stdout. If it did, the result would fail closed to unknown.
- **Suite status and inherited state.** I did not run the designated suites. The companion's inherited working state must be preserved, as plan 306–308 requires: `launcher.py` is modified, and `jevdrill_adapter.py` and `test_jevdrill_adapter.py` are untracked.

## Inspected paths

**JEV:**

- `plans/detailed-usage-reporting-20261001-1610.md` (full)
- `research/usage-review/`:
  - `reconciliation.md`
  - `round3/`: `delta.diff`, `delta-binding.json`, `carry-forward.json`, `claude/review-instructions.md`, `claude/review-bundle.md`, `claude/prompt.md`
  - `round2/`:
    - `reviewed-plan.md`
    - `claude/verdict.md`
    - `claude/review-bundle.md` (digests only)
    - `{codex,gemini,codex_adversarial}/verdict.md` (targeted)
  - `round1/president/ruling-2.md` (targeted)
  - `upstream/exec-lib.rs` (targeted)
- `.phase-loop/runs/PLAN-usage-reporting-20261001-1610/`: `exec-events.rs` and `exec-contract.rs` (targeted); `protocol.rs` (search only)
- `research/runtime-accounting/observations-20261001.json`
- Digest-checked only: `investigation-20261001.md`, `contracts.baml`, `ReportRequest.json`, `application.py`, `storage.py`, `host-interfaces.md`

**Companion (`phase-loop-runtime/`):**

- `src/phase_loop_runtime/`:
  - `jevdrill_adapter.py`: `prepare`, `launch`, `launch_jevdrill`
  - `launcher.py`: `LaunchSpec` and 2848–2858
- `tests/`: `test_jevdrill_adapter.py`, plus a grep across all tests
- Digest-checked only: `jevdrill_queue.py`

## Verdict rationale

The delta implements all four repair steps for R2-1, and each checks out against the pinned sources. The invalidator is exact and complete within the pinned scope, the message inspection is narrow, the negative control is required, and the residual is split in both documents. N-a and N-b are resolved, and the optional N-c fails safe. The changes only add rejection conditions and test obligations; contracts, wire format, scope and runtime sources are unchanged. No blocking defect remains.

AGREE
