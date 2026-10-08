# Detailed plan: Linux internal V0 routing deployment

## Task

Owner approval on October 1, 2026 authorizes a Linux-first internal V0 focused
on routing and reporting, with automatic learning, background experiments and
policy promotion disabled. Prepare and verify a local installed package and
one actual model task through the existing agent-harness bridge. This is
local-only work: no commit, push, package publication, merge, fleet default
change, scheduler installation or paid API request. Keep the full roadmap's
cross-platform and later-stage acceptance requirements open.

## Research summary

The current task checkout contains verified CONTRACT/ROUTE foundations plus
uncommitted HOST/LEARN/EXPERIMENT implementation. It has 742 passing Linux
tests, but its live Gemma study is development-only and cannot supply release
promotion evidence. The harness exposes JevDrillTransport and JevDrillAdapter,
which invoke a separate installed CLI, recheck identity/authority and use a
persistent reporting queue. The CLI has no execution or promotion authority
by default. CPython 3.13 and BAML/bridge 0.20.1 remain pinned.

Use the isolated branch codex/v0-linux based on the existing task's ROUTE
checkpoint. Import the explicitly listed current implementation files without
changing or cleaning the original checkout. Imported changes are pre-existing
task work, not new output of this bounded plan.

## Changes

### Inherited implementation snapshot (copy; preserve source checkout)

Copy current tracked modifications and nonignored untracked files only under
src/**, baml_src/**, schemas/**, scripts/**, tests/**, docs/**, plans/**,
specs/**, research/evaluation/host/** and research/evaluation/pilot/**, plus
README.md, pyproject.toml, uv.lock and .github/workflows/host.yml.
These inputs are task-owned code, generated contracts, documentation and
purpose-built development fixtures; do not copy provider response artifacts,
credentials, .env files, private corpora, old operational state or caches.
The source is /mnt/workspace/worktrees/viperjuice/jevdrill-contract.
Read its matching evidence/*/verification.json only as metadata, preserving
historical scopes rather than claiming fresh platform acceptance.

Regression-fixture amendment: additionally read and copy the current
evidence/CONTRACT/coverage.json metadata and the exact purpose-built historical
fixtures evidence/EXPERIMENT/pilot-authorization.json,
evidence/EXPERIMENT/pilot/results.json and
evidence/EXPERIMENT/pilot/review-v2-results.json. Existing regression tests replay
these non-sensitive development responses through local fixtures. Preserve
their bytes and record hashes; copying an old authorization artifact grants no
current provider call or experiment authority. Never copy or use the original
paid pilot's operational database. All other provider artifacts stay excluded.

### specs/phase-plans-v1.md (modify)

Add the approved internal V0 checkpoint and its dependencies on CONTRACT,
ROUTE and scoped HOST proof. It can precede complete EXPERIMENT/PREPARE.
Keep all full-release exit criteria and cross-platform obligations unchanged.
Route the checkpoint to this plan; do not declare full PREPARE complete.

### scripts/verify_v0_release.py (create)

Use existing verification helpers for full Linux software checks. Build wheel
and source archive; verify contents; install actual locked runtime dependencies
and wheel in an isolated environment. Confirm imports and CLI work outside the
checkout, exercise durable decision/replay/report persistence, reinstall over
the prior ROUTE wheel and check migration/recovery, and preserve old/new artifacts
and rollback instructions. Default mode performs no model generation.

Explicit --live performs at most two ordinary subscription CLI generations:
one tiny independently checked readiness task to establish only a scoped
development quality/latency observation, then one routed task through the real
host adapter using the installed JEV CLI. Use the host's current visible default
model and supported low effort; verify subscription login and model catalog.
Use read-only sandbox, ephemeral mode, ignored user config, purpose-built
disposable task context and no requested hard token/spending ceiling.
Each call has 120-second wall-clock limit; no retry or model substitution.
Durably record attempts before dispatch, preserve uncertain outcomes on restart,
and never refresh this grant by rerunning. No API keys are retrieved or passed.

The fixture uses no optional guidance, JEV judgment, scheduler, experiments or
promotion. Advertise only observed/catalog identity and explicitly scoped
development checks. Prices, immutable weights revision and unobserved counters
remain unknown. Do not infer production quality, savings or full support.
Record host queue delivery/restart and final selected/applied identity.
Use existing supervised launcher and adapter methods; do not modify the
companion repo or patch/mimic executor success.

### tests/verification/test_v0_release.py (create)

Test the release reducer and admission boundaries: stale/mismatched wheel or
source binding, incomplete Linux checks, missing live completion, failed answer
checks, missing durable report/replay, unknown costs and retained call attempts.
Local fixture tests authorize no live execution.

### docs/v0-deployment.md (create); README.md (modify)

Document exact local install path/package hash, scope, manual harness wiring,
verification, upgrade/rollback, known platform limitations and disabled
automation. Link the release checkpoint from README, preserving research notes.
Clearly distinguish a scoped installed smoke proof from a ready fleet default.

### evidence/V0/** and .phase-loop/runs/V0-linux-20261001/** (create)

Own the release manifests, derived verification and purpose-built smoke inputs,
outputs and queue databases. This explicitly permits these outputs to be read.
Never serialize credentials, user data or hidden reasoning. Store only model
final answer and relevant model/usage/event metadata from the ephemeral CLI.
Keep source/wheel/companion identities and failed/unknown evidence explicit.

## Documentation impact

This is an internal checkpoint under JD-046, not a cross-platform public
release. No schema or vocabulary identifiers change. Frozen route terms remain
RouteInputs, RoutingDecision, ExecutionRun and ReportRequest; reuse their
existing schema definitions rather than adding a second contract catalog.

## Dependencies & order

1. Preserve initial status; establish isolated checkout and import scoped source.
2. Amend roadmap and register this plan; write plan handoff before implementation.
3. Implement verifier and fixture controls; install dependencies; run targeted checks.
4. Freeze artifacts, run full Linux checks and installed/migration verification.
5. Run bounded live readiness and routed task only after software checks pass.
6. Reduce V0 evidence; record exact deployment/rollback details and limitations.
   A failed scoped proof blocks V0 without changing the full phase verdicts.

## Verification

- uv sync --locked; npm ci --ignore-scripts --no-audit --no-fund
- .venv/bin/python -m pytest -q tests/verification/test_v0_release.py
- .venv/bin/python -m ruff check scripts/verify_v0_release.py tests/verification/test_v0_release.py
- .venv/bin/python -m ruff format --check scripts/verify_v0_release.py tests/verification/test_v0_release.py
- PATH="$PWD/.venv/bin:$PATH" BAML_CLI=/home/viperjuice/workspace/tmp/jevdrill/gemma-compiler/bin/baml-cli JEVDRILL_AGENT_HARNESS_ROOT=/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port .venv/bin/python scripts/verify_v0_release.py --prepare
- The same environment: .venv/bin/python scripts/verify_v0_release.py --live
- .venv/bin/python scripts/verify_v0_release.py --reduce-only
- git diff --check -- README.md specs/phase-plans-v1.md plans/detailed-v0-linux-20261001.md scripts/verify_v0_release.py tests/verification/test_v0_release.py docs/v0-deployment.md
- /home/viperjuice/.local/share/uv/tools/phase-loop-runtime/bin/python -m phase_loop_runtime.closeout_classifier --repo .

automation.suite_command: .venv/bin/python scripts/verify_v0_release.py --reduce-only

## Acceptance criteria

- [ ] Approved V0 scope and retained full-release obligations are documented.
- [ ] Full Linux software checks pass against the source bound to the candidate.
- [ ] Wheel installs with locked real dependencies and imports from its isolated
      environment; prior ROUTE install upgrades with durable records intact.
- [ ] Live subscription task completes under the installed route/report bridge,
      passes its independent check, and preserves selected/applied identity.
- [ ] Durable reports are acknowledged after queue restart; exact routing replay
      remains stable; no automatic learning, experiments or promotion is enabled.
- [ ] Release manifest identifies package/source/companion hashes, install target,
      limitations and rollback procedure without secrets or performance claims.
