# HOST readiness

"Readiness" is this file's name, not a claim. This page says what HOST has on `main`, how a run is made, what the one run shows and what it does not show. No HOST criterion is verified and no gate exists. The plan is the [HOST plan](../plans/phase-plan-v1-HOST.md); the host integration's interfaces are in [HOST interfaces](host-interfaces.md).

## On `main`

- **The verifier,** `scripts/verify_host_phase.py`. On each native runner it collects one receipt: the inherited ROUTE regressions with the HOST controls added, the companion's own tests at the pinned commit, and the conformance fixture's witness. Its reduction reads the three receipts of the workflow run it is part of; a local collection is a diagnostic that no reduction reads.
- **Its tests,** `tests/verification/test_host_phase.py`.
- **The workflow,** `.github/workflows/host.yml` (`HOST verification`): one native job on each of hosted Linux, macOS and Windows, then a reduce job.
- **The conformance tests and probes:** `tests/conformance/` (a fixture module, five test files and one fixture) and `research/evaluation/host/test_bridge_probe.py` and `test_baseline_probe.py`, beside the synthetic protocol `research/evaluation/host/protocol.json`. The conformance tests are among the verifier's controls, and the conformance fixture runs the two probes in a child process.
- **The records:** [`evidence/HOST/coverage.json`](../evidence/HOST/coverage.json), each clause of the plan's tables with its status and controls; [`evidence/HOST/spec-delta.json`](../evidence/HOST/spec-delta.json), the closeout record, whose `closeout_status` is `verification_pending`; and [`evidence/HOST/adapter-handoff.json`](../evidence/HOST/adapter-handoff.json), which names the pinned host-integration commit, Consiliency/agent-harness `a06a952e8ff1c96bb5ec40a88be6b65edb468a7b`, its package version 0.7.39 and the digests of five modules.

## How a run is made

```sh
gh workflow run host.yml --repo Consiliency/jevdrill --ref main -f companion_ref=<40-hex commit SHA>
```

The workflow runs only when dispatched. Its one input, `companion_ref`, is required. Before the host integration is checked out, the native and the reduce jobs each refuse a value that is not the full commit `adapter-handoff.json` names. The workflow's permission is `contents: read`, and it uses no secret. Each native job syncs the host integration and runs `verify_host_phase.py --local-only`; the reduce job downloads the native receipts and runs `--reduce-only`.

## The run

[Run 45121428848](https://github.com/Consiliency/jevdrill/actions/runs/45121428848) was dispatched on 2026-11-23 on `main` at `cf3c9926abcbdc09a34823334693df42568f771a`, with the handoff's commit. Its conclusion is `failure`.

| Job | Result as recorded |
| --- | --- |
| [native (ubuntu-latest, Linux)](https://github.com/Consiliency/jevdrill/actions/runs/45121428848/job/137515866020) | `success` |
| [native (macos-latest, Darwin)](https://github.com/Consiliency/jevdrill/actions/runs/45121428848/job/137515865965) | `success` |
| [native (windows-latest, Windows)](https://github.com/Consiliency/jevdrill/actions/runs/45121428848/job/137515865778) | `failure`, at the step that runs `verify_host_phase.py --local-only` |
| [reduce](https://github.com/Consiliency/jevdrill/actions/runs/45121428848/job/137519269431) | `failure`, at "Require successful native jobs"; every later step `skipped` |

## Why it has no verdict

On Windows the collector stopped before any test ran, with `HOST collection failed: the companion did not import`. The import went through `provider_tree_proof.py:48` of the host integration at the pinned commit, which reads `select.POLLIN`, and the job's log shows `AttributeError: module 'select' has no attribute 'POLLIN'`. This is Consiliency/agent-harness#2092. The Windows artifact holds only the platform and that error. Because a native job failed, the reduce job stopped at its first check: the reduction did not run, and the run has no `host-verification` artifact.

## The Linux and macOS receipts

Each of the two jobs ran the verifier's own check on its own receipt alone, and that check reported no error (`"local_errors": []` in each job's log). No reduction examined either receipt, and nothing is verified. Both receipts name jevdrill at `cf3c9926a` and the host integration at `a06a952e8`, each with a clean checkout, and both name run 45121428848.

## Time

The collection bound is 600 seconds. The roadmap says: "Flag proof-cost limits when single-node evaluation exceeds roughly five minutes or cannot report multiple failures" ([roadmap](../specs/phase-plans-v1.md), line 354), and the verifier flags a collection over 300 seconds. The Linux receipt records 417 seconds and the macOS receipt 569 seconds, 31 seconds inside the bound. Both carry `proof_cost_target_exceeded: true`.

## Red and green

A run is green only if every job succeeds. The reduce job's reduction step succeeds only if the verdict's `status` is `"passed"`, which needs no receipt error and no clause not covered; only such a verdict lists `IF-0-HOST-1` under `produced_if_gates`. Under the plan as it stands no run can be green: `coverage.json` holds nine clauses as not covered, the verifier holds the same nine as constants, and each one blocks the gate. They are:

- EC-HOST-1: "Acceptance failures supply bounded rerouting context: the host half".
- EC-HOST-1: "Deactivates at task end, reporting host limitations".
- EC-HOST-2: "That explicit reports enter the same queue".
- EC-HOST-2: "Disconnects include supported resolution advice".
- EC-HOST-4: "The harness may retain its current model: a launch that keeps it".
- Scope notes: "the readiness recheck before launch"; "the budget passed after host spawn time"; "ordinary macOS execution staying local"; "the absence of silent forwarding".

One more clause, EC-HOST-3's "A live development or validation evaluation", is outside the plan's reading. It does not block, and a verdict lists it under `outside_reading`.

A red run is one of two kinds. If a native job fails, the reduction does not run and there is no verdict, as in this run. If every native job succeeds, the reduction runs and uploads a verdict whose `status` is `"blocked"`; its `controls_passed` says whether the reduction found any error other than the clauses not covered. A new pin that lets Windows import does not by itself make a run green: with no receipt error, the verdict is still `"blocked"`, with `controls_passed: true` and no gate.

## Artifacts

Receipts (`host-native-Linux`, `host-native-Darwin`, `host-native-Windows`) and any verdict (`host-verification`) are artifacts of the run that made them, and GitHub deletes them under its artifact retention. This run's three artifacts expire on 2027-02-21. The verifier's outputs under `evidence/HOST/` are ignored by git, and a verdict is never committed. A receipt's digests show that its content is consistent with itself and with the two checkouts; that it came from this run rests on the workflow's artifact boundary, not on the digests.

## Not shown

- Windows: no Windows receipt holds a test result.
- Any reduction of the receipts.
- Any criterion: EC-HOST-1 to 4, IF-0-HOST-1 or IF-0-VC-2.
- The gate.
