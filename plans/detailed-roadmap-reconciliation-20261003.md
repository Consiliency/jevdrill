# Detailed plan: reconcile roadmap evidence and refresh Linux V0

## Task

Continue the approved roadmap recommendations. Reuse the task-owned V0 and
companion worktrees, preserve inherited changes and all live grants/results,
and complete local verification before proposing new live studies or activation.
This bounded step is local-only: no provider execution, publication, adoption,
fleet default change, scheduler installation, archive-key provisioning or policy
promotion. The existing phase EC text and platform obligations remain unchanged.

## Research summary

CONTRACT/ROUTE reports in this candidate are stale. Historical HOST/LEARN PASS
and EXPERIMENT BLOCKED records are in the prior task worktree. The V0 import
excluded phase evidence, including required LEARN/EXPERIMENT digest inputs.
Existing collectors and reducers can refresh proof without a new framework.
The installed-package verifier supports preparation separately from live execution;
its original run must stay frozen. Native macOS and Windows SSH probes succeed.

## Changes

- `src/jevdrill/costing.py`: repair the type-check failure exposed by the
  original CONTRACT verifier. Finite rates have integer Decimal exponents,
  but the standard-library annotation also permits nonfinite sentinel strings.
  Convert the already-validated finite exponent to `int` before taking its
  absolute value for precision sizing. Existing costing controls verify exact
  arithmetic and invalid-rate rejection; no rate or metric semantics change.
- `tests/conformance/test_usage_reporting.py` and the companion
  `phase-loop-runtime/tests/test_jevdrill_usage.py`: repair native conformance
  portability exposed on actual macOS/Windows. Use native interpreter paths and
  a native Python executable for the controlled Windows process. Retain exact
  receipt assertions on supported Linux capture; unsupported native platforms
  must retain unknown counts and absent input manifests, with real queue/replay
  checks and no skipped cases. Prototype in owned private copies before changing
  source while a collector is running. Preserve failed native diagnostics.
- `scripts/verify_route_phase.py`, `scripts/verify_host_phase.py` and
  `tests/verification/test_host_phase.py`: give the expanded HOST offline proof
  a bounded 600-second collection budget, with a separately configurable internal
  ROUTE collector budget for that call. Ordinary ROUTE proof retains its existing
  300-second limit. Test rejection beyond the new HOST limit. This changes an
  offline test budget only; routing deadlines and experiment limits are unchanged.
  Exclude generated `.egg-info` installer indexes from companion source hashing,
  alongside existing bytecode exclusions. Native investigation found the
  installed SOURCES.txt index alone caused fixture mismatch. Keep actual source,
  tests, shared schemas and packaged-resource bytes bound; verify both generated
  metadata independence and real resource mutation in the existing freshness test.

- `evidence/ROADMAP/**`: archive the exact historical phase metadata, record
  source paths and hashes, and create an EC-by-EC reconciliation and execution
  handoff. No historical verdict is relabeled as current proof.
- `evidence/HOST/**`, `evidence/LEARN/**`, `evidence/EXPERIMENT/**`: recover
  missing coverage and spec-delta inputs verbatim, with provenance in ROADMAP;
  run existing collectors/reducers for current native evidence. Keep original
  reports archived before any collector replaces their current projection.
  Re-run the existing restricted development-runtime verifier against an already
  installed, inspected image with Node. The old Node 24 image is absent; the
  installed public postgres-meta image provides Node 22 and the standard Node
  entrypoint with no credential-named image environment fields. Pin its inspected
  image ID and record this changed runtime provenance. Use only the existing
  restricted runner, no host mounts/network or service entrypoint, and no model
  calls. No image download or existing service/container change is authorized.
- `evidence/CONTRACT/**`, `evidence/ROUTE/**`: preserve current reports and
  manifests in ROADMAP history, then refresh using their original verifiers.
  Align ROUTE's deferral list with CONTRACT's accepted phase ownership: JD-078
  now belongs to EXPERIMENT. Remove its obsolete ROUTE deferral entry while
  preserving the requirement in CONTRACT and the experiment plan.
- `evidence/V0-refresh/**` and `.phase-loop/runs/ROADMAP-20261003/**`: own
  isolated package/dependency/upgrade/replay verification, private runner scripts,
  logs, source bindings, status snapshots and closeout. Invoke the existing V0
  preparation implementation with separate run/evidence roots. Never invoke live
  mode or copy, reset or renew any authorization database.
- `docs/v0-deployment.md`, `docs/roadmap-status.md`: update the installation
  handoff and current verified/blocked status using the new evidence. The frozen
  vocabulary and public BAML report contracts remain unchanged.
- `plans/manifest.json` and `.dev-skills/handoffs/**`: record execution lifecycle
  and continuation pointers. Native test fixtures may be copied into an owned
  private descendant of the existing regression checkout; preserve its original
  snapshot and establish exact source/test equivalence before using a copy.

Read allowance: the preceding owned paths; current and prior worktree
`evidence/{CONTRACT,ROUTE,HOST,LEARN,EXPERIMENT}/*.json` and
`platforms/*.json`, prior `evidence/EXPERIMENT/local-gemma/{summary.md,analysis.json,verification.json}`,
phase plans and public sources/tests/docs/scripts; primary
`research/baml-proof/README.md`; metadata of the existing V0/REPORT installed
packages and previously used grant ledgers (hash/row-count checks only); the
regression checkout's public source/tests/config. Credentials, raw provider
transcripts and user corpora are excluded. This step does not read old paid
pilot databases. Read-only native tool/version/access probes and isolated native
verification jobs are authorized; source snapshots and artifacts stay in task
directories without deleting remote files or changing machine security policy.

## Documentation impact

Update V0 installation/rollback paths and the roadmap status. Keep historical
scope explicit and current failures visible. No new schema, metric or vocabulary
identifier is introduced by this metadata/package reconciliation.

## Dependencies and order

1. Capture starting dirty paths; register this plan and archive original metadata.
2. Restore missing inputs with hashes and validate the current EC coverage map.
3. Refresh locked dependencies and run targeted verifier controls.
4. Run original native collectors, starting with Linux; inspect failures before
   repairing or repeating checks. Stage isolated source snapshots on accessible
   native hosts only after Linux checks establish a stable candidate.
5. Refresh isolated V0 package/upgrade/replay proof without a model dispatch.
6. Reduce actual evidence, update handoff and report precise remaining gaps.
   Subsequent feature work or study execution requires its own bounded plan.

## Verification

- `uv sync --locked`; `npm ci --ignore-scripts --no-audit --no-fund`.
- `.venv/bin/python -m pytest -q tests/contracts/test_phase_verification.py tests/verification/test_route_phase.py tests/verification/test_host_phase.py tests/verification/test_learn_phase.py tests/verification/test_experiment_phase.py tests/verification/test_v0_release.py`.
- Original `scripts/verify_{contract,route,host,learn,experiment}_phase.py`
  collectors and reducers, with pinned BAML 0.20.1 and explicit companion/test
  fixture paths. Native matrix failures remain blocked; local PASS produces no
  full platform gate.
- Existing `verify_v0_release.prepare()` under separate owned roots; it runs the
  full Linux suite and locked isolated installation plus baseline upgrade/replay.
- `.venv/bin/python scripts/verify_development_runtime.py --image-id sha256:9a079ac1c94d89629262822a4bd1902d5b1be4adb464e5a0a8fd078aaed72158`.
- `git diff --check` in both task-owned worktrees; hash/metadata checks verify
  that all earlier live grants/results are unchanged.

automation.suite_command: .venv/bin/python scripts/verify_experiment_phase.py --local-only

## Acceptance criteria

- [ ] Historical records have immutable copies and source/hash provenance.
- [ ] Missing phase digest inputs are restored without fabricated verdicts.
- [ ] Every roadmap EC is linked to verified evidence, a concrete implementation
      gap or an operational dependency; untouched EC text is referenced by ID.
- [ ] The fresh Linux package installs with locked dependencies and retains
      baseline routing replay across upgrade; no live dispatch occurs.
- [ ] Original verifiers expose actual current native failures and missing
      operational evidence; no blocked full phase is reported as passed.
- [ ] Handoff identifies exact install/rollback artifacts, current limitations,
      next bounded implementation work and any human decision with its reason.
