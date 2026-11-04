**Do not merge Consiliency/jevdrill#1 at `a92d65ca021672100d53ff50001f1a2a8f9d85ac`.** Two integration/verification blockers remain.

1. **P2 — Narrowing ROUTE breaks downstream collection. M1/M3.**

   The [new test selection](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/scripts/verify_route_phase.py:133) includes all 22 declared ROUTE controls. However, [HOST](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/scripts/verify_host_phase.py:443) and [LEARN](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/scripts/verify_learn_phase.py:442) still invoke that collector, and downstream reducers require their own assertions within its results.

   **Trigger/consequence:** collecting HOST, LEARN, or EXPERIMENT now omits **9 HOST, 30 LEARN, and 31 EXPERIMENT required controls**. Companion-only tests do not supply those jevdrill assertions. Substituting the actual successful current-head ROUTE receipt into an otherwise valid synthetic HOST input produced exactly nine missing-control errors.

   Separately, [synthetic reducer fixtures](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/tests/verification/test_learn_phase.py:23) retain historical command lists, causing six reproducible `stale command coverage` failures. Updating those fixtures alone would leave the production collector defect.

   **Minimal repair:** preserve standalone ROUTE’s independence while explicitly executing and binding downstream suites in their collectors. Update synthetic command fixtures and retain every required assertion. This follows the existing [LEARN verification requirements](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/plans/phase-plan-v1-LEARN.md:78).

2. **P2 — Floating-point arithmetic falsely reports omitted overhead. M3.**

   The [study driver](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/scripts/verify_discovery_calibration.py:1464) constructs total duration using chained addition; validation at lines 460 and 907 compares it against `sum(...)`.

   **Trigger/consequence:** synthetic durations `[0.0, 0.1, 0.7, 1.0]` produce a driver total of `1.7999999999999998`, but validation computes `1.8` and returns `omitted overhead`. Complete telemetry can therefore fail validation. Current-head [EXPERIMENT CI](https://github.com/Consiliency/jevdrill/actions/runs/38320714705) failed with that unexpected diagnostic: **211 passed, 1 failed**.

   **Minimal repair:** use consistent summation in construction and validation, with a deterministic rounding regression control. Preserve rejection of genuinely omitted duration; no empirical tolerance decision is needed.

The prior findings are adjudicated as follows:

- **SDK publication — closed, M1/M3.** All 147 outputs are tracked. A clean `git archive HEAD` imports and builds successfully; its wheel includes the four patch modules and attribution files. Clean-archive generation matches **147 outputs / 78 schemas**.
- **Provider restriction — closed, M1/M2.** The [allowlist guard](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/application.py:758) precedes built-in and injected dispatch. Six allowed/denied controls pass; provider identity also binds judgment templates and cache identity.
- **Bearer/Basic disclosure — closed, M2.** [Redaction](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/context.py:16) consumes scheme and credential. Submission and retained-content controls pass.
- **Recovery replenishment — closed through restriction, M2.** [Import persists the admission block](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/storage.py:1244); application and transactional admission guards enforce it. Restore/restart cannot replenish authority. This does **not** restore the omitted ledger.
- **Completed-worker deletion — closed, M2.** [Cancellation](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/storage.py:433) reaches terminal workers, and the worker scrub removes frozen inputs/configuration/observations. The regression passes without refunding reservations.
- **Discovery retention — closed, M1/M2.** Durable artifact association, tombstone checks, archival, expiry, retry, and deletion controls pass. An additional synthetic archive→restore→cross-producer deletion probe passed. Omitting raw discovery content from portable v1 recovery is a documented limitation consistent with its metadata-lineage guarantee, not a promise of complete restoration.
- **Windows source binding — closed, M3.** LF configuration precedes native checkouts. Current-head ROUTE receipts from Linux/macOS/Windows have identical digests matching local source.
- **Companion/CI completeness — repair incomplete, M3.** Standalone ROUTE succeeds, but the downstream regression above remains blocking.

Verification actually performed:

- **110 targeted tests passed:** packaging, CLI, provider/privacy, execution, recovery, and retention.
- **95 verifier tests passed; 6 failed**, reproducing the supplied full-suite failures.
- Inspected the completed parent suite: **868 passed, 6 failed, zero skips**.
- Inspected fresh, current-head [CONTRACT](https://github.com/Consiliency/jevdrill/actions/runs/38320714711) and [ROUTE](https://github.com/Consiliency/jevdrill/actions/runs/38320714835) receipts: respectively **322 and 408 tests per native platform**, zero skips, all named checks successful, matching local digests.
- Publication path/high-confidence credential-pattern checks found no flagged files. `git diff --check` flags preserved historical evidence whitespace/CRLF; this is not an additional blocker.

Before/after checks passed for all **744 tracked files**. Manifest SHA-256 remained `542b6827ed820a553f8d7ff4fcd49d8db83e76ec9f7a396904f636759da600c7`; HEAD and clean tracked status remained unchanged.

No source/evidence edits, nested agents, real provider calls, credential access, actual grants/studies, adoption, or GitHub messages occurred. I inspected native receipts rather than rerunning native hosts. F6/F7/D2/D4/D6 remain unratified study concerns; I found no additional demonstrated merge blocker from them. This review grants no empirical acceptance.

DISAGREE
