**Do not merge Consiliency/jevdrill#1 at `a92d65ca021672100d53ff50001f1a2a8f9d85ac`.** Round 2 closes several original reproductions, but five concrete blockers remain.

1. **P1 — Discovery’s injected adapter bypasses request authority. M1/M2.**
   [application.py:284](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/application.py:284) delegates preparation to the injected adapter when it implements `prepare_option`. The shipped [DevelopmentJudge:197](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/integrations/development.py:197) checks its configured authorization callback but never receives the request’s privacy restrictions.

   Using that actual adapter against loopback, each request with `local_only=true`, `allowed_providers=["local"]`, `enabled=false`, or `cloud_allowed=false` dispatched **two HTTP requests** and returned `selected_guidance`. The allowed control also dispatched two. This violates the approved [before-every-call restriction](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/plans/phase-plan-v1-ROUTE.md:220).

   **Repair:** enforce request authority in Application before dispatch through either built-in or injected discovery adapters. Exercise the shipped adapter in denied controls.

2. **P1 — JSON-form credentials still reach judgment and retention. M2.**
   The regex at [context.py:16](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/context.py:16) misses quoted keys. Both `{"Authorization": "Bearer SYNTHETIC_R2_CREDENTIAL"}` and `{"api_key": "SYNTHETIC_R2_CREDENTIAL"}` passed through Application, reached the judgment callback, and persisted in raw-task artifacts. Both routes returned `ready`. The unquoted Authorization-header control was correctly redacted.

   This violates the [prohibition on collecting secrets](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/docs/jevdrill-spec.md:394). **Repair:** cover standard quoted credential assignments and verify submission and persisted bytes. The original unquoted-header reproduction is closed; the privacy blocker is only partially repaired.

3. **P1 — Cancellation clears worker records but leaves raw content in SQLite bytes. M2.**
   [DevelopmentRunner._db:589](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/integrations/development.py:589) leaves SQLite secure deletion disabled. `_save` removes sensitive fields logically, but previously stored bytes remain.

   An actual loopback completion with a **41-byte synthetic output**, followed by task deletion and explicit cancellation, produced controller/worker status `canceled`, zero logical observations, and no `frozen_inputs`. Nevertheless, the worker database file still contained both the raw task and output sentinel; `PRAGMA secure_delete` returned `0`.

   This violates [coordinated database/artifact deletion](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/docs/jevdrill-spec.md:373). **Repair:** scrub worker database storage, including previously freed content and applicable journals, and verify bytes after cancellation and restart.

4. **P1 — Imported task tombstones omit experiment cleanup. M2.**
   The deletion merge at [storage.py:1371](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/storage.py:1371) removes routing/learning material but omits direct deletion’s experiment cancellation and proposal cleanup. Consequently, [Experiments.execute:191](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/experiments.py:191) still returns completed jobs immediately.

   I completed a real synthetic worker, exported Application-produced recovery data, deleted the task in a recovered replica, and imported that replica’s tombstone into the original database. After restart and `advance`, the task was tombstoned but the execution remained `completed`; its proposal, frozen inputs, and **two readable retained observations** remained. No further dispatch occurred.

   This violates [deletion propagation during recovery](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/plans/phase-plan-v1-LEARN.md:66). **Repair:** apply direct deletion’s durable experiment cleanup when merging imported tombstones, preserving charged reservations.

5. **P2 — Narrowing ROUTE breaks downstream verification collectors. M3.**
   [HOST:443](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/scripts/verify_host_phase.py:443) and [LEARN:442](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/scripts/verify_learn_phase.py:442) still obtain their JEV assertions from `route.collect`; EXPERIMENT inherits that collection. Separate companion tests do not supply these missing JEV assertions.

   Actual collection of the revised ROUTE command found 408 tests and every required ROUTE control, but omitted **9/10 HOST, 30/30 LEARN, and 31/31 EXPERIMENT controls**. Downstream reducers still require them. Thus the stated preservation of downstream collectors is incorrect.

   I also independently reproduced all **six** failures in the parent’s final full-suite report: positive LEARN/EXPERIMENT reducer cases reject `stale command coverage`.

   **Repair:** explicitly collect and bind each downstream phase’s required JEV tests, update synthetic command fixtures, and preserve required assertions and historical receipts.

The other prior findings are adjudicated as follows:

- **SDK omission closed:** all 147 outputs are tracked; tracked-only archive imports passed; generation passed with **147 outputs / 78 schemas**, `write=false`.
- **Task judgment allowlist bypass closed:** the Application gate and allowed/denied controls cover built-in and injected task judges. Finding 1 concerns the separate discovery path.
- **Reservation replenishment closed:** persistent recovery admission blocking is a valid fail-closed repair. It does not claim ledger restoration. Finding 4 concerns deletion propagation.
- **Discovery retention closed for the reviewed paths:** archival, expiry, retry, cross-producer maintenance, and deletion controls passed. The documented omission of raw discovery artifacts from portable v1 export is consistent with metadata-only recovery and does not independently block merge.
- **Windows LF repair closed:** configuration precedes checkout; current-head CONTRACT and ROUTE native checks and reducers succeeded. The ROUTE companion repair remains incomplete because of finding 5.

Verification and limits:

- **225 targeted tests passed:** [JUnit receipt](/tmp/jevdrill-r2-redteam-tests.xml).
- **Six reducer failures independently reproduced:** [JUnit receipt](/tmp/jevdrill-r2-redteam-reducer-tests.xml). The parent’s supplied full-suite XML records **874 tests, six failures, zero skips**.
- Current-head [EXPERIMENT CI](https://github.com/Consiliency/jevdrill/actions/runs/38320714705) also failed: **211 passed, one failed**, with unexpected `omitted overhead` in the `[3-optional]` loopback control. I inspected that failure; I did not independently reproduce its timing condition.
- Before/after manifest checks passed. HEAD and tracked bytes remained unchanged; manifest SHA-256 is `542b6827ed820a553f8d7ff4fcd49d8db83e76ec9f7a396904f636759da600c7`.
- No nested agents, real providers, credentials, actual studies, holdouts, source/evidence edits, or GitHub messages. No additional M4 publication violation was demonstrated. Native matrix execution was observed through GitHub, not rerun independently.

These are demonstrated merge-criterion violations under M5, not requests for empirical acceptance or a new study grant.

DISAGREE
