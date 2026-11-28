# HOST readiness

"Readiness" is this file's name, not a claim. This page says what HOST has on `main`, how a run is made, what one run shows and what it does not show. No HOST criterion is verified and no gate exists. The plan is the [HOST plan](../plans/phase-plan-v1-HOST.md); the host integration's interfaces are in [HOST interfaces](host-interfaces.md).

## On `main`

- **The verifier,** `scripts/verify_host_phase.py`. On each native runner it collects one receipt in two timed parts. The inherited part is one call of the ROUTE collector, with ROUTE's own command. HOST's part is the rest: HOST's controls, in a command of the HOST collector's own; the companion's own tests at the pinned commit; and the witness the conformance fixture writes. Its reduction counts only the three receipts that record the workflow run and attempt it is part of; a receipt that records no workflow run, or another run or attempt, is a diagnostic, and the reduction rejects it.
- **Its tests,** `tests/verification/test_host_phase.py`.
- **The workflow,** `.github/workflows/host.yml` (`HOST verification`): one native job on each of hosted Linux, macOS and Windows, then a reduce job.
- **The conformance tests and probes:** `tests/conformance/` (a fixture module, five test files and one fixture) and `research/evaluation/host/test_bridge_probe.py` and `test_baseline_probe.py`, beside the synthetic protocol `research/evaluation/host/protocol.json`. The conformance tests are among the verifier's controls, and the conformance fixture runs the two probes in a child process.
- **The records:** [`evidence/HOST/coverage.json`](../evidence/HOST/coverage.json), each clause of the plan's tables with its status and controls; [`evidence/HOST/spec-delta.json`](../evidence/HOST/spec-delta.json), the closeout record, whose `closeout_status` is `verification_pending`; and [`evidence/HOST/adapter-handoff.json`](../evidence/HOST/adapter-handoff.json), which names the pinned host-integration commit, its package version and the digests of five modules. The run this page reports was made when it named Consiliency/agent-harness source commit `85b29c76ecfb8cf5a94523e7da84edc44dcd250f` (in-tree version 0.7.41); it now names `3a588dd19a52a28e4e5b2cd786e2799f381cdd15` (0.7.42), at which no run has been made yet.

## How a run is made

```sh
gh workflow run host.yml --repo Consiliency/jevdrill --ref main -f companion_ref=<40-hex commit SHA>
```

The workflow runs only when dispatched. Its one input, `companion_ref`, is required. Before the host integration is checked out, the native and the reduce jobs each refuse a value that is not the full commit `adapter-handoff.json` names. The workflow's permission is `contents: read`, and it references no repository secret. Each native job syncs the host integration and runs `verify_host_phase.py --local-only`; the reduce job downloads the native receipts and runs `--reduce-only`.

## The run

[Run 45294995110](https://github.com/Consiliency/jevdrill/actions/runs/45294995110) was dispatched on 2026-11-24 (UTC) on `main` at `72d3450d97ffb3fb7dc7dc812bf26dfcb687df92`, with the handoff's commit at the time, `85b29c76ecfb8cf5a94523e7da84edc44dcd250f`. Its conclusion is `failure`.

| Job | Result as recorded |
| --- | --- |
| [native (ubuntu-latest, Linux)](https://github.com/Consiliency/jevdrill/actions/runs/45294995110/job/138113015486) | `success` |
| [native (macos-latest, Darwin)](https://github.com/Consiliency/jevdrill/actions/runs/45294995110/job/138113014976) | `success` |
| [native (windows-latest, Windows)](https://github.com/Consiliency/jevdrill/actions/runs/45294995110/job/138113015450) | `success` |
| [reduce](https://github.com/Consiliency/jevdrill/actions/runs/45294995110/job/138119971362) | `failure`, at the step that runs `verify_host_phase.py --reduce-only`; the next step uploaded the verdict |

Each native job ran the verifier's own check on its own receipt alone, and that check reported no error (`"local_errors": []` in each job's log). The reduction then ran on the three receipts. Its verdict is the run's `host-verification` artifact. The three receipts name jevdrill at `72d3450d9` and the host integration at `85b29c76e`, each with a clean checkout, and all three name run 45294995110, attempt 1.

## Why the run shows as failed

The reduce step exits with an error whenever the verdict's `status` is not `"passed"`, and this verdict's `status` is `"blocked"`. That step is the only one in the run that failed: every step of the three native jobs succeeded, and every other step of the reduce job succeeded or, after it, was skipped. The failure marks the blocked verdict; it is not an error in a receipt.

## The verdict

The `host-verification` artifact holds one file, `verification.json`. Its fields, quoted:

- `"status": "blocked"`.
- `"controls_passed": true`.
- `"errors": []`.
- `"not_covered"`: the nine clauses listed under "Red and green" below, as `"EC-HOST-1/host-limitations"`, `"EC-HOST-1/rerouting-context-host"`, `"EC-HOST-2/disconnect-advice"`, `"EC-HOST-2/explicit-reports-same-queue"`, `"EC-HOST-4/retain-model-launch"`, `"scope/budget-after-host-spawn"`, `"scope/no-silent-forwarding"`, `"scope/ordinary-macos-execution-local"` and `"scope/readiness-recheck-before-launch"`.
- `"outside_reading": ["EC-HOST-3/live-evaluation"]`.
- `"produced_if_gates": []`.

It also names jevdrill at `72d3450d9`, the host integration at `85b29c76e`, run 45294995110, attempt 1, and the platforms `Darwin`, `Linux` and `Windows`.

**What `controls_passed: true` means here.** In this run the reduction found no error in the three receipts: every control the verifier requires was present with its exact count and recorded as passed on each platform where it runs. That is all it means, and three limits stand beside it:

- the evidence is synthetic software conformance (each receipt's witness records `"claim_scope": "synthetic_conformance_only"`), and the plan's ["This plan may not claim"](../plans/phase-plan-v1-HOST.md#this-plan-may-not-claim) lists what it cannot support;
- nine clauses of the plan are not covered: `coverage.json` names no control for any of them;
- the reduction examines receipts written by the job that ran the code under test; a receipt is not an independent attestation.

## No gate

`produced_if_gates` is empty. The nine clauses not covered each block the gate; they are listed under "Red and green" below, with Consiliency/jevdrill#120. No HOST criterion is closed, and a run does not close one.

## Time

The collection has two bounds: the inherited part within ROUTE's own 600 seconds, and HOST's part within 900 seconds. A receipt with a part over its bound is rejected. The roadmap says: "Flag proof-cost limits when single-node evaluation exceeds roughly five minutes or cannot report multiple failures" ([roadmap](../specs/phase-plans-v1.md), line 354), and the verifier flags a collection over 300 seconds. The receipts give these times, in seconds:

| Receipt | Inherited part | HOST's part | Total |
| --- | --- | --- | --- |
| Linux | 72.4 | 284.1 | 356.5 |
| macOS | 147.2 | 496.4 | 643.6 |
| Windows | 93.0 | 466.9 | 559.9 |

Each part is inside its bound. All three totals are over the five-minute flag: each receipt carries `proof_cost_target_exceeded: true`, and the verdict's `proof_cost_over_five_minutes` names all three platforms.

## Red and green

A run is green only if every job succeeds. The reduce job's reduction step succeeds only if the verdict's `status` is `"passed"`, which needs no receipt error and no clause not covered; only such a verdict lists `IF-0-HOST-1` under `produced_if_gates`. Under the plan as it stands no run can be green: `coverage.json` holds nine clauses as not covered, with no control for any of them, the verifier holds the same nine as constants, and each one blocks the gate. They are listed in Consiliency/jevdrill#120:

- EC-HOST-1: "Acceptance failures supply bounded rerouting context: the host half".
- EC-HOST-1: "Deactivates at task end, reporting host limitations".
- EC-HOST-2: "That explicit reports enter the same queue".
- EC-HOST-2: "Disconnects include supported resolution advice".
- EC-HOST-4: "The harness may retain its current model: a launch that keeps it".
- Scope notes: "the readiness recheck before launch"; "the budget passed after host spawn time"; "ordinary macOS execution staying local"; "the absence of silent forwarding".

One more clause, EC-HOST-3's "A live development or validation evaluation", is outside the plan's reading. It does not block, and a verdict lists it under `outside_reading`.

A run can be red in three ways:

- **A collection stops with an error.** Its receipt holds only that error, its native job fails, and the reduce job stops at its first check.
- **A receipt is rejected by its job's own check,** as when a part runs past its bound. Its native job fails, and the reduce job stops at its first check.
- **The reduction runs to its end and the verdict is `"blocked"`.** Every native job succeeds; the reduction writes the verdict, the reduce step fails, and the next step uploads the verdict as the run's artifact. Its `controls_passed` says whether the reduction found any error other than the clauses not covered. This run is red this way, with `"errors": []` and `controls_passed: true`.

Any step can also fail or be cancelled, and then there may be no verdict.

## Artifacts

Receipts (`host-native-Linux`, `host-native-Darwin`, `host-native-Windows`) and the verdict (`host-verification`) are artifacts of the run that made them, and GitHub deletes them under its artifact retention. This run's four artifacts expire on 2027-02-22. GitHub records these digests for them:

| Artifact | Digest |
| --- | --- |
| `host-verification` | `sha256:db26c0d5967ea843ec62d8888a58b3ebfe95790248d58ec9874ddda2398b11de` |
| `host-native-Linux` | `sha256:312afa68136c1e70df8f43250673bfdd8d1bdf4be6dcd44389e90e257162cf76` |
| `host-native-Darwin` | `sha256:c7094c31d7faba84722490ae2580012d31f59cda85f6bf587aa0db4bf409eeb2` |
| `host-native-Windows` | `sha256:909707c702d6be85592075a8841ac03fa308fe5e7ebc8b6f4f1c9e3fa34fef93` |

The verifier's outputs under `evidence/HOST/` are ignored by git, and a verdict is never committed. A receipt's digests show that its content is consistent with itself and with the two checkouts; that it came from this run rests on the workflow's artifact boundary, not on the digests. A receipt is not an independent attestation: the code under test ran in the job that wrote it.

## Not shown

- Any criterion: EC-HOST-1 to 4, IF-0-HOST-1 or IF-0-VC-2.
- The gate.
- The nine clauses not covered, and the live evaluation outside the plan's reading.
- Anything beyond synthetic software conformance; the plan's ["This plan may not claim"](../plans/phase-plan-v1-HOST.md#this-plan-may-not-claim) applies in full.
- An observed exit-4 deletion answer, on any platform. The conformance tests through the delete path at `85b29c76e` passed on all three platforms; no receipt holds a deletion answered with exit code 4.
- A check of the receipts by anything other than the run that wrote them.
