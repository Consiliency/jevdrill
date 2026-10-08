# Advisory Review: Observed Codex Usage in JEV Drill Reports

- **Seat**: Gemini
- **Lens**: alternative-approach
- **Review Round**: 1
- **Status**: Manual Advisory Review (Non-governed implementation gate)
- **Primary Artifact**: `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-usage-reporting-20261001-1610.md`

## Executive Summary

The overall objective of the plan—retaining observed terminal token counters from Linux Codex `exec` 0.159.2 runs and delivering them durably into JEV Drill without modifying wire schemas—is technically sound and well-grounded in the October 1 investigation findings.

However, an alternative-approach evaluation reveals several architectural tensions, leaky abstractions, and edge-case vulnerabilities in the proposed design across `launcher.py` and `jevdrill_adapter.py`. Specifically:
1. Embedding JEV Drill BAML `UsagePayload` schema knowledge directly into `launcher.py` introduces unnecessary coupling and dual-authority conflicts between the general harness and the JEV adapter.
2. The stream reader and drainage protocol in `launcher.py` suffers from a race condition on process exit where unread stdout lines can be dropped.
3. Ignoring "presentation text" on stdout contradicts fail-closed machine `--json` mode and risks skipping oversized or malformed protocol items.
4. Spawning an unmemoized `codex --version` subprocess inside the critical execution path of every launch adds needless latency and deadline complexity.
5. Pinned upstream Codex source reveals that compaction is not emitted on stdout JSONL, rendering stdout-based compaction detection unprovable.

Addressing these findings with the proposed alternative approaches will yield a cleaner separation of concerns, greater stream reliability, and a more robust implementation.

---

## Actionable Findings

### AA-01 — High — Blocker: Decouple `LaunchResult` carrier from JEV Drill BAML contracts
- **Plan Section**: Section 7 (lines 120–125), Companion `launcher.py` (lines 137–147), Behavior 5–7.
- **Affected Acceptance Criteria / Invariant**: AC1, AC3; Architectural invariant: Clean separation of concerns between general execution harness (`launcher.py`) and JEV Drill bridge (`jevdrill_adapter.py`).
- **Problem**:
  The plan mandates that `launcher.py` store a `UsagePayload`-shaped JSON mapping in optional `LaunchResult.jevdrill_usage`. This forces `launcher.py` (a general-purpose execution engine across multiple executors and harnesses) to construct JEV Drill-specific BAML structures (`metric_id`, `metric_version`, `counting_semantics`, `parent_metric_id`, `method="codex_exec_jsonl_0_159_2_v1"`, and `source="host"`).
  Meanwhile, `jevdrill_adapter.py:launch` *already* owns measurement creation (`completion_time_ms`, `quality_score`, lines 474–484). The plan states that the adapter "validates the receipt and replaces only the four unknown token measurements".
  Having `launcher.py` construct a partial BAML `UsagePayload` creates a dual-authority problem over measurement formatting, duplicates JEV Drill schema knowledge in the companion launcher, and prevents other consumers of `LaunchResult` (e.g. `observability.py`, handoffs) from using normalized token counts without parsing BAML domain structures.
- **Alternative Approach**:
  Define a clean, executor-normalized observed usage dictionary on `LaunchResult` (e.g. `observed_token_usage: dict[str, int] | None = None` containing `input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_tokens`, and `cli_version`).
  Let `jevdrill_adapter.py`—whose sole domain responsibility is translating between `agent-harness` and JEV Drill contracts—map these integer counters into the BAML `Measurement` records with their registered method, source, and subset semantics.
- **Smallest Repair**:
  Update Section 7 and the Companion `launcher.py`/`jevdrill_adapter.py` change boundaries so `LaunchResult` carries an executor-normalized token dict, and `jevdrill_adapter.py` maps and validates those values into the final BAML `UsagePayload`.

---

### AA-02 — High — Blocker: Replace premature polling break with an explicit join-and-drain protocol
- **Plan Section**: Behavior 3 (lines 90–96), Companion `launcher.py` (lines 141–144).
- **Affected Acceptance Criteria / Invariant**: AC1, AC5; Invariant: Stream integrity, complete output drainage, and non-lossy capture.
- **Problem**:
  In `launcher.py` (lines 2963–2981), when `process.poll() is not None`, the loop performs a non-blocking `get_nowait()` on `line_queue` until empty and then immediately breaks out to `process.wait()` and `reader.join(timeout=1)`.
  When splitting stdout and stderr into separate reader threads, lines still buffered in the OS pipe or in transit in reader threads when the process exits will cause `get_nowait()` to hit `Empty` prematurely. The main loop exits, and any subsequently queued lines are orphaned.
  Additionally, the existing `_read_lines` puts `None` in `line_queue` on any exit, making clean EOF indistinguishable from a reader exception (e.g. `UnicodeDecodeError` or `OSError`).
- **Alternative Approach**:
  Implement an explicit message-passing and drain protocol:
  1. Have reader threads push tagged items: `("stdout", line)`, `("stderr", line)`, `("stdout_eof", None)`, `("stderr_eof", None)`, and `("stdout_error", exc)`.
  2. Following process exit, the main loop must continue pulling from `line_queue` until BOTH EOF sentinels are received or a bounded post-exit timeout (e.g. 2.0s) expires.
  3. If an error sentinel is encountered or the drain timeout expires before both EOF sentinels arrive, record `drain_status = "incomplete"` and fail closed (invalidating known usage).
- **Smallest Repair**:
  Specify in Behavior 3 and `launcher.py` changes that stream reader threads must signal distinct EOF and error sentinels, and the supervisor must wait for both stream EOF sentinels during post-exit drainage before finalizing capture.

---

### AA-03 — High — Blocker: Eliminate "ignoring presentation text" on stdout in favor of a fail-closed parser
- **Plan Section**: Behavior 4 (lines 97–103), Companion `test_jevdrill_usage.py`.
- **Affected Acceptance Criteria / Invariant**: AC1, AC2; Invariant: Deterministic protocol boundaries and strict evasion prevention.
- **Problem**:
  Behavior 4 states: "Accept only top-level protocol events from stdout. Ignore presentation text, nested tool output and unknown item content; never copy them into the receipt or report."
  In `codex exec` with `--json`, stdout is strictly a machine JSONL stream (line 106 in pinned `exec-events.rs`). There is no legitimate top-level "presentation text" on stdout.
  If the parser silently ignores unparseable lines or presentation text, an oversized or malformed protocol event (e.g., an oversized `CollabToolCallItem` that exceeds 1 MiB or has duplicate keys) could be silently discarded as "presentation text". The parser would then proceed to `turn.completed` and falsely certify known usage despite missing an invalidating collaboration event.
- **Alternative Approach**:
  Adopt an irreversible fail-closed state machine for machine `--json` stdout capture:
  - Any non-empty line on stdout that is not a valid JSON object representing a recognized top-level `ThreadEvent`, or that exceeds 1 MiB, or has duplicate keys, MUST immediately transition the collector into an irreversible `UNKNOWN / INVALID` state.
  - No stdout line should be dismissed as ignorable presentation text; presentation text belongs on stderr.
- **Smallest Repair**:
  Amend Behavior 4 to remove "ignore presentation text" on stdout. Explicitly declare that any non-protocol line on stdout invalidates known usage for the run.

---

### AA-04 — Medium — Suggestion: Memoize CLI version qualification to eliminate per-launch subprocess overhead
- **Plan Section**: Behavior 2 (lines 84–89), Companion `launcher.py` (lines 140–141).
- **Affected Acceptance Criteria / Invariant**: AC5; Invariant: Minimal launch overhead and robust deadline preservation.
- **Problem**:
  Behavior 2 requires running an argv-based `--version` probe with a 1-second timeout inside the timed launch on every execution, deducting elapsed time from the execution deadline.
  In iterative phase loops and delegated sub-tasks, repeatedly spawning `codex --version` adds 100–300ms of subprocess latency to every launch and complicates timeout calculations. If a tight deadline is configured, the probe can consume a substantial fraction of the execution allowance.
- **Alternative Approach**:
  - Memoize the `--version` probe result keyed by the resolved executable canonical path and `st_mtime_ns` (`(os.path.realpath(cmd), os.stat(cmd).st_mtime_ns)`) within the runtime session.
  - Alternatively, perform the version qualification during candidate verification in `jevdrill_adapter.py:prepare()`, where model revision and route capabilities are already independently verified.
- **Smallest Repair**:
  Update Behavior 2 to allow session-level memoization of the version probe by canonical binary path and mtime, preserving the 1-second timeout and fail-unknown fallback on mismatch.

---

### AA-05 — High — Blocker: Narrow compaction exclusion claim to observable stream semantics
- **Plan Section**: Behavior 4 (lines 102–103), AC1 (lines 267–269).
- **Affected Acceptance Criteria / Invariant**: AC1; Invariant: Auditability and verifiability of acceptance criteria.
- **Problem**:
  Behavior 4 states that "compact/fork ambiguity ... invalidates known usage."
  However, source inspection of pinned `exec-events.rs:598` and `protocol.rs:1400` reveals that `codex exec` drops `ContextCompacted` server notifications (`_ => CodexStatus::Running`), emitting no event on stdout for compaction.
  An observer reading stdout JSONL cannot detect whether compaction occurred. Acceptance criterion AC1 cannot be satisfied or proven by `test_jevdrill_usage.py` for compaction.
- **Alternative Approach**:
  Explicitly acknowledge the protocol reality:
  - Document that the host observation method `codex_exec_jsonl_0_159_2_v1` is defined for single-turn, fresh-thread execution.
  - State that compaction events are not emitted by Codex 0.159.2 on stdout JSONL, and narrow AC1's exclusions to stream-observable conditions (turn/thread restarts, collaboration items, malformed records, EOF/drain errors, and duplicate terminal events).
- **Smallest Repair**:
  Remove the unprovable compaction exclusion requirement from Behavior 4 and AC1; record compaction unobservability as an explicit residual limitation in `docs/host-interfaces.md` and `docs/jevdrill-integration.md`.

---

### AA-06 — Low — Suggestion: Explicitly separate failure controls in test fixtures
- **Plan Section**: Behavior 6 (lines 118–119) vs Section "JEV tests/conformance" (line 181).
- **Affected Acceptance Criteria / Invariant**: AC1, AC3.
- **Problem**:
  Behavior 6 states that a valid observed snapshot may survive a later process failure (with `terminal="failed"` and no completion claim). Conversely, line 181 broadly says that failed observations stay unknown. This creates potential ambiguity for test authoring in AC1 and AC3.
- **Alternative Approach**:
  Clearly specify the two distinct failure fixtures in the conformance plan:
  - Subprocess crash/failure *before* valid terminal usage emission -> token usage is `unknown/not_reported`.
  - Valid `turn.completed` snapshot received, but process exits with a nonzero returncode -> token counters are preserved as observed, but the lifecycle event reports `failed` and `applied_plan_id=None`.
- **Smallest Repair**:
  Clarify this distinction in Section "JEV tests/conformance" and AC3.

---

## Inspected Paths & Verification Scope

The following 13 primary referenced files and 4 additional context files were inspected via local tools:
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-usage-reporting-20261001-1610.md`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/runtime-accounting/investigation-20261001.md`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/runtime-accounting/observations-20261001.json`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/contracts.baml`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/schemas/ReportRequest.json`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/application.py`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/storage.py`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/context.py`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/host-interfaces.md`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/vocabulary.yaml`
- `/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port/phase-loop-runtime/src/phase_loop_runtime/launcher.py`
- `/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port/phase-loop-runtime/src/phase_loop_runtime/jevdrill_adapter.py`
- `/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port/phase-loop-runtime/src/phase_loop_runtime/jevdrill_queue.py`
- `/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port/phase-loop-runtime/src/phase_loop_runtime/runner.py`
- `/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port/phase-loop-runtime/tests/test_jevdrill_adapter.py`
- `/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port/docs/jevdrill-integration.md`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/PLAN-usage-reporting-20261001-1610/exec-events.rs`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/PLAN-usage-reporting-20261001-1610/exec-contract.rs`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/PLAN-usage-reporting-20261001-1610/protocol.rs`
- `/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/scripts/verify_host_phase.py`

All SHA-256 hashes of the 13 reference files matched the prompt's inputs table exactly.

**Unverified Assumptions**:
- Live runtime execution characteristics of Codex CLI 0.159.2 under production load.
- Specific OS pipe buffer limits on the host machine.
- No live model calls, test suite executions, builds, or code changes were made during this advisory review.

---

## Verdict

PARTIALLY AGREE
