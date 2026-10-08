# Detailed plan: raw token costs from observed category counters

## Task

Continue authorized local accounting work after INPUT-v0. Use the existing JEV
worktree and preserve inherited work. The initial path uses caller-supplied,
versioned undiscounted rates; the owner may select a maintained price catalog
in the pending structured question. Implement only calculation independent of
rate discovery. No provider calls, commits, publication or phase-gate closure.

## Changes

1. Add `estimate_usage_cost` in `src/jevdrill/costing.py`, reusing AttemptCost
   and existing boundary checks. Accept already normalized portable integer
   input/output/cached-input counters and explicit per-token input, cached-input
   and output rates, currency, rate revision and optional separate subscription
   multiplier. Cached input is a subset of input. Compute uncached input plus
   cached input plus output exactly once; output already includes reasoning.
   Reject invalid counters, subsets, rates and missing revision. Missing counters
   or a rate needed for a positive category leave raw/adjusted costs unknown.
   A known zero category costs zero without inventing a missing price. Use
   sufficient local Decimal precision so ambient settings cannot alter results.
   Return raw and adjusted separately; observed invoice charges remain unknown.
   Rates must apply to the stated counter semantics. This calculator does not
   cover additional provider billing categories, cache writes, hidden calls,
   immutable identity verification, invoice totals or hard spending enforcement.
   Add controls in `tests/costing/test_costing.py`, including the historical
   smoke's counter values with explicitly synthetic prices.
2. Update `docs/route-interfaces.md` and `docs/host-interfaces.md` to describe
   category accounting and residual coverage. This is an internal scalar
   calculation API using existing CostEstimate/AttemptCost meanings, not a new
   wire contract. BAML remains authoritative; no schema or telemetry change.
3. Extend `scripts/verify_executor_input.py` with a separate `--cost` scope,
   distinct COST-v0 run/evidence paths and plan binding. Reuse its frozen install,
   wheel, lint, vocabulary and full JEV checks. For cost scope, run cost tests and
   an isolated installed-wheel calculation. Reuse the unchanged companion proof
   only after matching all companion source bindings against
   `evidence/INPUT-v0/verification.json`; do not rerun unrelated companion tests.
   Write `evidence/COST-v0/verification.json` and own metadata under
   `.phase-loop/runs/COST-v0-20261002`. Preserve previous evidence and live ledgers.

Workflow also owns this plan, `plans/manifest.json`, COST-v0 closeout, handoff
and skill reflection. Exact read permission includes INPUT-v0's verification
artifact plus source/test/schema/contract/docs globs and lockfiles already read
by the shared verifier. All other dirty files remain inherited and untouched.

## Verification

- Focused costing tests, changed-file lint and format checks.
- `BAML_CLI=/mnt/workspace/worktrees/viperjuice/.baml-v1-0201-toolchain/bin/baml-cli JEVDRILL_AGENT_HARNESS_ROOT=/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port .venv/bin/python scripts/verify_executor_input.py --cost`.
- Require installed import and arithmetic, frozen dependency refresh, source
  bindings, full JEV tests, no skipped cost controls and no non-plan output.

## Acceptance criteria

- [ ] Cached input and reasoning subsets are not billed twice.
- [ ] Missing counters/prices remain unknown; known zeros, invalid inputs and
  portable counter limits are handled correctly.
- [ ] Decimal results are deterministic; raw, adjustment and observed charges
  remain separate under a required explicit rate revision.
- [ ] Documentation describes price applicability and observation limits; no
  wire, routing ranking, policy, hard-ceiling or invoice claim changes.
- [ ] Source-bound synthetic cost evidence passes an installed wheel and full
  JEV suite while preserving INPUT/USAGE evidence, live grants and inherited work.
