# Estimated-cost routing and requested execution ceilings

## Task

Implement the user's 2026-09-29 decision: allow estimated-cost routing without
a requested hard ceiling; reject requested ceilings that cannot be enforced.

## Changes

- `baml_src/contracts.baml` and `baml_src/boundary.json`: add optional nullable
  `execution_token_limits` to `HardConstraints` and `CandidateSnapshot`, with
  positive `input_tokens` and `output_tokens` totals for one execution run.
  Omission means no requested token ceiling or no proven executor bounds,
  respectively. Context/output planning limits keep their existing meanings.
  Regenerate `schemas/**` and `src/baml_sdk/**` through the pinned generator.
- `src/jevdrill/application.py` and `src/jevdrill/routing.py`: retain estimated
  raw/adjusted costs for ranking; evaluate requested token, spending and retry
  ceilings using separate whole-run bounds. Estimates never prove ceilings.
  Keep rates unknown when unavailable, and use raw cost for hard spending limits.
  Version cross-request cache keys for the new policy; preserve immutable
  idempotent replay while preventing reuse of pre-policy decisions for new requests.
- `tests/application/test_application.py`, `tests/routing/test_routing.py` and
  `tests/contracts/test_host_contracts.py` and `test_boundaries.py`: cover optional-field compatibility,
  malformed bounds, estimated routing, enforced ceilings and retry budgets.
- Update active route/HOST interface and readiness docs, HOST roadmap/plan,
  vocabulary registry/glossary, JD-083 in `specs/jevdrill-design-input.md`, and
  metadata-only HOST handoff/checkpoint evidence.
  Extend `evidence/CONTRACT/coverage.json` with JD-083 and refresh JD-082's
  section digest after inserting the decision; preserve historical proof artifacts.
- In the already assigned companion worktree, amend its existing plan before
  modifying `jevdrill_adapter.py`, its tests, public schema fixtures and integration
  docs. Verify identity for all routes; require the final enforcement callback
  only when ceilings are requested. Check advertised bounds before dispatch.

## Verification

Run pinned contract generation and generation consistency, Python/Node contract
parity, targeted application/routing/companion tests, full JEV tests, vocabulary,
import, Ruff and mypy checks. Refresh copied companion schema digests and handoff.
Prior HOST/platform evidence remains historical after these contract changes.

## Acceptance criteria

- A verified executor without total-run caps can route and launch when no ceiling
  is requested, retaining estimates and unknown actual usage.
- Requested spending, retry-spend or token ceilings reject missing, insufficient
  or no-longer-enforceable bounds before execution.
- Raw estimates remain distinct from adjusted cost and observed usage; context
  capacity and per-request output limits never claim total-run enforcement.
- Existing omitted-field inputs remain valid; new fields reject malformed values.
- HOST stays incomplete until its separate platform and evaluation gates pass.
