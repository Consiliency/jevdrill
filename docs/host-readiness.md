# HOST readiness

"Readiness" is this file's name, not a claim. This page says what HOST has on `main`, how a run is made, what the one run shows and what it does not show. No HOST criterion is verified and no gate exists. The plan is the [HOST plan](../plans/phase-plan-v1-HOST.md); the host integration's interfaces are in [HOST interfaces](host-interfaces.md).

## On `main`

- **The verifier,** `scripts/verify_host_phase.py`. On each native runner it collects one receipt: the inherited ROUTE regressions with the HOST controls added, the companion's own tests at the pinned commit, and the conformance fixture's witness. Its reduction counts only the three receipts that record the workflow run and attempt it is part of; a receipt that records no workflow run, or another run or attempt, is a diagnostic, and the reduction rejects it.
- **Its tests,** `tests/verification/test_host_phase.py`.
- **The workflow,** `.github/workflows/host.yml` (`HOST verification`): one native job on each of hosted Linux, macOS and Windows, then a reduce job.
- **The conformance tests and probes:** `tests/conformance/` (a fixture module, five test files and one fixture) and `research/evaluation/host/test_bridge_probe.py` and `test_baseline_probe.py`, beside the synthetic protocol `research/evaluation/host/protocol.json`. The conformance tests are among the verifier's controls, and the conformance fixture runs the two probes in a child process.
- **The records:** [`evidence/HOST/coverage.json`](../evidence/HOST/coverage.json), each clause of the plan's tables with its status and controls; [`evidence/HOST/spec-delta.json`](../evidence/HOST/spec-delta.json), the closeout record, whose `closeout_status` is `verification_pending`; and [`evidence/HOST/adapter-handoff.json`](../evidence/HOST/adapter-handoff.json), which names the pinned host-integration commit, Consiliency/agent-harness source commit `85b29c76ecfb8cf5a94523e7da84edc44dcd250f` (in-tree version 0.7.41), and the digests of five modules.

## How a run is made

```sh
gh workflow run host.yml --repo Consiliency/jevdrill --ref main -f companion_ref=<40-hex commit SHA>
```

The workflow runs only when dispatched. Its one input, `companion_ref`, is required. Before the host integration is checked out, the native and the reduce jobs each refuse a value that is not the full commit `adapter-handoff.json` names. The workflow's permission is `contents: read`, and it references no repository secret. Each native job syncs the host integration and runs `verify_host_phase.py --local-only`; the reduce job downloads the native receipts and runs `--reduce-only`.

## The run

[Run 45236348900](https://github.com/Consiliency/jevdrill/actions/runs/45236348900) was dispatched on 2026-11-23 on `main` at `af87ded53a5d02dfd05cd3335a4bf4e75fddcf2a`, with the handoff's commit. Its conclusion is `failure`.

| Job | Result as recorded |
| --- | --- |
| [native (ubuntu-latest, Linux)](https://github.com/Consiliency/jevdrill/actions/runs/45236348900/job/137909003697) | `success` |
| [native (macos-latest, Darwin)](https://github.com/Consiliency/jevdrill/actions/runs/45236348900/job/137909004141) | `success` |
| [native (windows-latest, Windows)](https://github.com/Consiliency/jevdrill/actions/runs/45236348900/job/137909003932) | `failure`, at the step that runs `verify_host_phase.py --local-only` |
| [reduce](https://github.com/Consiliency/jevdrill/actions/runs/45236348900/job/137917670552) | `failure`, at "Require successful native jobs"; every later workflow step `skipped` |

## Why it has no verdict

The Windows receipt was written, uploaded and rejected. Its collection ran past the 600-second bound, with the inherited test command unfinished and the companion's tests ended by the deadline. The collector wrote the receipt, the job's next step uploaded it as `host-native-Windows`, and the job's own check on it reported errors, so the job failed. Because a native job failed, the reduce job stopped at its first check: the reduction did not run, and the run has no `host-verification` artifact.

## The Windows receipt

- **The collector's import check of the host integration succeeded on Windows.** The receipt records the five modules the handoff names, and the job's own check reported no error about them. That shows the host integration imports there; it shows nothing of how it behaves.
- **The collection did not finish.** JEV Drill's inherited test command was stopped when the inherited collection's 600 seconds ran out; the last progress mark pytest printed in the job's log is 85 per cent. The companion's tests were then started with none of the HOST collection's 600 seconds left, and the deadline stopped them (`deadline_expired: true`). The HOST static check was stopped the same way.
- **No Windows receipt holds a complete result.** The receipt records no test outcome from the inherited test command and none from the companion's tests.
- **Its other errors follow from the cut-off.** The job's log lists 57 errors in all. Apart from the bound and the stopped commands, they report controls and checks with no result because those commands were stopped; they are not separate failures.

## The Linux and macOS receipts

Each of the two jobs ran the verifier's own check on its own receipt alone, and that check reported no error (`"local_errors": []` in each job's log). No reduction examined either receipt, and nothing is verified. Both receipts name jevdrill at `af87ded53` and the host integration at `85b29c76e`, each with a clean checkout, and both name run 45236348900. The receipts hold synthetic software-conformance results, and the times below are collection durations; the plan's ["This plan may not claim"](../plans/phase-plan-v1-HOST.md#this-plan-may-not-claim) lists what they cannot support.

## Time

The collection bound is 600 seconds. The roadmap says: "Flag proof-cost limits when single-node evaluation exceeds roughly five minutes or cannot report multiple failures" ([roadmap](../specs/phase-plans-v1.md), line 354), and the verifier flags a collection over 300 seconds. The receipts give these times, in seconds:

| Receipt | Whole collection | Inherited collection | Its test command | Rest |
| --- | --- | --- | --- | --- |
| Linux | 481.6 | 433.5 | 417.5 | 48.1 |
| macOS | 536.9 | 506.8 | 493.5 | 30.1 |
| Windows | 605.4 | 600.1 | 597.5, stopped | 5.3 |

Linux finished 118 seconds inside the bound and macOS 63 seconds inside it; Windows ran 5.4 seconds past it. All three receipts carry `proof_cost_target_exceeded: true`. The rest is the whole collection less the inherited collection: it holds the import check, the companion's tests, the HOST static check and the collector's other work, and the receipts record no time for any of them. Neither the log nor the receipts split the inherited test command's time between the ROUTE tests and HOST's paths: the log shows only each command's result, or on Windows pytest's progress, and the receipts record each test's outcome without its time.

## Red and green

A run is green only if every job succeeds. The reduce job's reduction step succeeds only if the verdict's `status` is `"passed"`, which needs no receipt error and no clause not covered; only such a verdict lists `IF-0-HOST-1` under `produced_if_gates`. Under the plan as it stands no run can be green: `coverage.json` holds nine clauses as not covered, the verifier holds the same nine as constants, and each one blocks the gate. They are listed in Consiliency/jevdrill#120:

- EC-HOST-1: "Acceptance failures supply bounded rerouting context: the host half".
- EC-HOST-1: "Deactivates at task end, reporting host limitations".
- EC-HOST-2: "That explicit reports enter the same queue".
- EC-HOST-2: "Disconnects include supported resolution advice".
- EC-HOST-4: "The harness may retain its current model: a launch that keeps it".
- Scope notes: "the readiness recheck before launch"; "the budget passed after host spawn time"; "ordinary macOS execution staying local"; "the absence of silent forwarding".

One more clause, EC-HOST-3's "A live development or validation evaluation", is outside the plan's reading. It does not block, and a verdict lists it under `outside_reading`.

A run can be red in three ways:

- **A collection stops with an error.** Its receipt holds only that error, its native job fails, and the reduce job stops at its first check.
- **A receipt is rejected by its job's own check,** as when a collection runs past the 600-second bound. Its native job fails, and the reduce job stops at its first check. This run is red this way.
- **The reduction runs to its end.** If every native job succeeds, the reduction writes a verdict whose `status` is `"blocked"`, and the next step uploads it as the run's artifact; its `controls_passed` says whether the reduction found any error other than the clauses not covered.

Any step can also fail or be cancelled, and then there may be no verdict. Three collections that fit the bound do not by themselves make a run green: with no receipt error, the verdict is still `"blocked"`, with `controls_passed: true` and no gate.

## Artifacts

Receipts (`host-native-Linux`, `host-native-Darwin`, `host-native-Windows`) and any verdict (`host-verification`) are artifacts of the run that made them, and GitHub deletes them under its artifact retention. This run's three artifacts expire on 2027-02-21. The verifier's outputs under `evidence/HOST/` are ignored by git, and a verdict is never committed. A receipt's digests show that its content is consistent with itself and with the two checkouts; that it came from this run rests on the workflow's artifact boundary, not on the digests. A receipt is not an independent attestation: the code under test ran in the job that wrote it.

## Not shown

- Windows: no Windows receipt holds a complete result. In particular, the deletion of a task through the pinned host integration's delete path, against `main`'s deletion answer (exit code 4 while deleted content is not yet erased), has a conformance outcome on Linux and macOS only, and no receipt records a deletion answered with exit code 4.
- How the inherited test command's time divides between the ROUTE tests and HOST's paths.
- Any reduction of the receipts.
- Any criterion: EC-HOST-1 to 4, IF-0-HOST-1 or IF-0-VC-2.
- The gate.
