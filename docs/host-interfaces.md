# HOST interfaces

This page describes the host integration at the commit [`evidence/HOST/adapter-handoff.json`](../evidence/HOST/adapter-handoff.json) pins: Consiliency/agent-harness source commit `85b29c76ecfb8cf5a94523e7da84edc44dcd250f` (in-tree version 0.7.41). The two modules it draws on are [`jevdrill_adapter.py`](https://github.com/Consiliency/agent-harness/blob/85b29c76ecfb8cf5a94523e7da84edc44dcd250f/phase-loop-runtime/src/phase_loop_runtime/jevdrill_adapter.py) and [`jevdrill_queue.py`](https://github.com/Consiliency/agent-harness/blob/85b29c76ecfb8cf5a94523e7da84edc44dcd250f/phase-loop-runtime/src/phase_loop_runtime/jevdrill_queue.py), under `phase-loop-runtime/src/phase_loop_runtime/`. It describes code at that commit, not behaviour a run has shown; [HOST readiness](host-readiness.md) says what the reported run shows. It is a summary: it does not list every refusal or failure path, and the code at that commit is the authority.

## Commands

`JevDrillTransport.call` spawns the JEV Drill CLI at most once per call. Before the spawn it checks the request against its schema, the 1,000,000-byte limit and the deadline, and any of these can refuse the call; after the CLI exits it validates the response.

| Command | Request | Response |
| --- | --- | --- |
| `discover` | `DiscoveryInputs` | `DiscoveryResult` |
| `route` | `RouteInputs`, or `DiscoveryRouteInputs` when `schema_version` is `"2"` | `RoutingDecision` |
| `inspect-discovery` | `DiscoveryInspectRequest` | `DiscoveryResult`, or exactly `{"schema_version": "1", "status": "not_found"}` |
| `delete-discovery` | `DiscoveryDeleteRequest` | exactly `{"schema_version": "1", "status": "deleted", "work_objective_id": …}` |
| `report` | `ReportRequest` | `ReportAcknowledgment` |
| `notices` | `NoticeRequest` | `NoticeInbox` |
| `delete` | `DeleteRequest` | exactly `{"schema_version": "1", "status": "deleted", "task_id": …}` |

The schemas are in [`schemas/`](../schemas/). The host integration carries copies of them, and the collector compares those copies with jevdrill's files.

- `discover`, `route`, `report` and `notices` send the request on standard input; `inspect-discovery`, `delete-discovery` and `delete` give it as command-line arguments. `inspect-discovery` refuses a replay request.
- A request and a response are each limited to 1,000,000 bytes. Standard error is discarded.
- Output over the limit, or a stream that did not finish in time, is refused whatever the exit code; only after exit code 0 or 3 is the response examined, and it can still be refused: invalid JSON, a duplicate key, a `NaN`, `Infinity` or `-Infinity` constant, a response outside its contract, or an expired deadline. After validation, exit code 3 raises unless the command is `report` and the acknowledgment's status is `conflict`. Any other exit code, or a failed write of the request, raises.
- Every command but `delete` is given `--remaining-budget-ms`: the allowance left when the command line is built, before the spawn, and at least 1.

## The 5-second allowance

A call's deadline is 5 seconds after the `started_at` it is given, or after the call begins when it is given none. A call whose allowance is spent before the spawn is refused; a call that outlives it is killed and raises `TimeoutError`. Calls given one `started_at` share one allowance:

| Logical operation | Calls that share one allowance |
| --- | --- |
| Discovery (`discover_objective`) | `notices`, `discover` |
| Routing a task (`prepare`) | `notices`; for a task linked to a discovery, `inspect-discovery`; `route` |
| Delivering one queued report (`flush`) | `notices`, `report` |
| Deleting an objective (`delete_objective`) | `notices`, `delete-discovery` |

The hosted run publishes no measurement of the full allowance.

At launch, a linked task's `inspect-discovery` recheck has an allowance of its own, and so does `delete` for a task. For discovery and routing, the allowance starts before the objective lifecycle lock is taken, so time spent waiting for that lock counts against it. The wait for the lock is itself bounded at 5 seconds.

## Notices

Before each `discover`, each `route`, each `delete-discovery` and each queued report's delivery, the adapter calls `notices` for the project, workspace and producer, with operation `report` for a report and `route` otherwise. It hands each notice returned to the host's `notice_sink` callback. If the sink raises, the adapter records a `notice_delivery_failed` warning and goes on. A failed `notices` call raises before the command it precedes is called: no `discover`, `route` or `delete-discovery` call follows, and in a delivery the report is not sent, and the queue's delivery rules below decide what happens to it. In an objective deletion the local tombstone is already written by then. The same sink receives the queue's dispositions: a report that was not queued, the disposition counts after a delivery, an invalid usage receipt and a failed delivery.

## The queue

`ReportQueue` is one SQLite file, and each adapter opens one. For a routed launch the adapter offers the run's lifecycle and usage reports to the queue, and enqueue can refuse them (below); a launch that was not routed makes no report.

- **Limits:** 16 MiB of stored reports, 10,000 reports, 1 MiB per report, and seven days' retention. `sanitize_report` refuses a report over the transport's 1,000,000-byte limit, with a `ValueError`, before it is stored, so through the adapter no report reaches the queue's 1 MiB limit. A report seven days old or older is removed and counted when a queue operation (enqueue, delivery or a status read) runs and its transaction commits, not on a timer.
- **File:** on Linux and macOS it is created with mode 0600 in a directory created with mode 0700; on Windows the code opens it through a private bound directory, with a persistent journal. On Windows the module takes that path whenever it creates the queue or opens a transaction, and in the hosted Windows job the 15 tests of the companion's `tests/test_jevdrill_queue.py` recorded `passed`. The host integration's tests of its Windows storage module, `tests/test_windows_storage.py` at that commit, are not among the companion's tests, and no receipt holds their outcome.
- **Before any write,** each report goes through the adapter's `sanitize_report`.
- **Enqueue** returns `queued`, `duplicate` (same event, same content), `conflict` (same event, different content), `deleted` (the task has a tombstone) or `overflow`. Conflicts, deletions, overflows and expiries are counted. Enqueue can also raise.
- **Delivery** takes the oldest pending report whose retry time has come. A delivery removes the report only when the acknowledgment names the same event, has status `accepted` or `duplicate`, and has `durable` true. An acknowledgment that names the same event with status `conflict` or `rejected` and `durable` false marks the report and is counted. Any other acknowledgment, or an `OSError`, `TimeoutError` or `ValueError` from the call, schedules a retry after min(300, 2^min(attempts, 9)) seconds; any other exception, such as a response that fails its schema, leaves the queue unchanged and propagates. Expiry and task deletion also remove reports.
- **`flush`** attempts at most one delivery per call, of the oldest eligible report, which need not be the current run's. The routed launch path calls it once, after offering the run's terminal, usage and any deactivation reports; if an exception escapes that step before it, `flush` is not called; an invalid usage receipt is handled inside the step and does not stop it.
- **Deletion:** deleting a task writes a tombstone and removes the task's queued reports, before JEV Drill is called. Deleting an objective writes an objective tombstone and removes its bindings, before JEV Drill is called.
- **Corruption:** a failed integrity check or a corrupt database writes a marker file, and the marker blocks every later use of the queue. Nothing in the module removes it.

## The companion's environment

- **Sync:** `uv sync --project .host/companion/phase-loop-runtime --group test --extra visual --locked --python 3.12`, in `host.yml`. The host integration's own workflow uses the same options.
- **Python:** 3.12 for the host integration; JEV Drill runs on 3.14. The run's receipts record 3.12.16 on Linux and 3.12.10 on macOS and Windows.
- **The interpreter** reaches the collector as `JEVDRILL_AGENT_HARNESS_PYTHON`, and the collector refuses to collect without it.
- **Variables (the HOST verifier's test configuration):** the host integration's test command is given only these. `PATH`, `LANG`, `LC_ALL`, `LC_CTYPE`, `TMPDIR`, `TEMP`, `TMP`, `SYSTEMROOT`, `SystemRoot`, `WINDIR`, `COMSPEC` and `PATHEXT`, where set. `HOME` and `USERPROFILE`, pointing at an empty temporary home. `NO_PROXY` and `no_proxy`, set to `127.0.0.1,localhost`. `PYTHONPATH`, the checkout's `src` and `tests`. `JEVDRILL_TEST_CLI` and `JEVDRILL_TEST_PYTHON`, the installed JEV Drill command and its Python. `PHASE_LOOP_TDD_EXPECT_SCHED=1`.
- **Command (the HOST verifier's test configuration):** pytest with `-m "not dotfiles_integration"` over seven test files on Linux. On macOS and Windows, `test_jevdrill_input.py`, `test_jevdrill_usage.py` and `test_jevdrill_diagnostics.py` are left out.

## Dry runs

- A decision made for a dry-run request carries a diagnostic with the code `dry_run_decision`. The learning-observation builder skips any decision that carries it; a test checks this in the store that took the decision and in a fresh store after an export and an import. The adapter at the pinned commit sends no dry-run route.
- A cached decision is reused only for a request of the same mode. The cache lookup returns the lowest-numbered matching decision, so a dry-run request whose lowest-numbered cached decision predates the diagnostic is decided afresh each time.
- A dry run decided before the diagnostic existed is not excluded.
- An import does not detect a bundle that misstates a decision's mode: a dry run whose diagnostic was removed is counted, and a real decision given the diagnostic is not.
- Analysis evidence saved before the diagnostic existed, and any policy promoted on it, keeps its counts until it is replaced.

## Limits the plan states

- **A decline is not visible to learning.** When the host declines a recommendation, no routed run starts, and learning sees a host preference only as a choice among runs that happened.
- **Usage capture is exercised on Linux only.** The usage, input and diagnostics test files run only in the Linux command.
- **The deselected launcher tests are not exercised.** The 53 tests of the `dotfiles_integration` class in `test_phase_loop_launcher.py` are deselected. They cover launcher skill and adoption bundle building, and the execute path that resolves a dotfiles skill source and profile overlay.
