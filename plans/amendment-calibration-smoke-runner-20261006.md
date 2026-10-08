# Bind the repaired BAML client to the one-case smoke runner

## Task and authority

The owner requested continuation after approving the pinned client repair. Implement and validate the prepared one-case runner. Keep the existing dedicated worktree and preserve inherited edits. This bounded preparation does not dispatch live calls; separate execution authority is required before live mode.

## Changes

- Add private runner, generated task SDK, controls and ledgers under `.phase-loop/runs/CALIBRATION-smoke-20261006/**`.
- Read the frozen `smoke-proposal.json`, budget proposal, calibration corpus, prior provider protocol and routing-comparison ledger. Reuse `scripts/verify_routing_contracts.py`, the production application and JEV adapter. These exact historical files and their existing snapshot dependencies are authorized read inputs; do not change them.
- Save reservations before every outbound request, including each JEV request inside a route. Record sanitized callbacks with a callback-local SQLite connection. Keep uncertain attempts non-retryable. Use one process lock per study.
- Isolate task SDK generation/response parsing from the product SDK. Validate raw output before semantic grading. Keep one case, five arms, at most five generations and four JEV calls, existing timeouts, no retries, and the unchanged $2 cumulative guard.
- Bind sources and protocol before execution. Reject changed sources, missing authorization, wrong endpoints, excess calls, incomplete schedule admission and credential leakage. Provide offline loopback controls and zero-dispatch replay.
- Write evidence under `evidence/EXPERIMENT/calibration-smoke-20261006/**`, handoff and reflection. Keep previous evidence and roadmap verdicts unchanged. No publication.
- On authorized completion, update `evidence/ROADMAP/latest-study.json` while retaining its complete previous record.

## Adopted live execution authority

The owner subsequently answered: “Run the scoped live smoke test (Recommended). Checks the repaired BAML path and accounting with the existing provider keys.” Structured question reference: `call_TTuX4GkUW5DjrbuOwbOd53Ci`. The exact source/protocol binding and approved limits are in `evidence/EXPERIMENT/calibration-smoke-20261006/authorization.json`. This authorizes the one prepared case only, including retained reservations for missing usage; it does not authorize retries, additional cases or promotion.

## Verification

Run the actual runner with a synthetic loopback provider using the product routing path and separate task SDK. Verify nine requests maximum, all five arms, independent grading, callback persistence, exact replay, uncertain-attempt nonretry, source binding failures and full-schedule admission. Check that missing authorization prevents live dispatch. Parse and inspect all output evidence; run syntax/lint checks on new runner files and `git diff --check`.

## Acceptance criteria

- The prepared runner follows the frozen first case and arm order, uses BAML for every model call, and reserves before every dispatch.
- Offline controls pass without live credentials, retain unknown reservations, and replay without requests.
- The $0.855004000 maximum new reservation fits only if the authoritative carried commitment still permits it under $2.
- The executable runner and its exact source/protocol digests are reviewable before live authorization. No calibration quality or promotion claim follows from this one-case smoke test.
