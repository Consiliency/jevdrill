# Aggregate conformance watchdog correction (2026-10-18)

`tests/conformance/conftest.py` raises the single combined bridge and baseline
pytest subprocess watchdog from **300 to 420 seconds**. The child still runs both
files in the same order and process, followed by the separate 120-second discovery
child. `tests/conformance/test_usage_reporting.py` raises the whole companion
usage probe watchdog from **20 to 30 seconds**. Each usage case still executes
the same installed CLI, queue, and replay checks.

These are aggregate test-process allowances for multiple independent operations,
not product acceptance budgets. The five-second logical operation and replay
deadlines and the 600-second HOST collector hard limit are unchanged. See
`plans/phase-plan-v1-HOST.md` lines 37 and 141,
`scripts/verify_host_phase.py` lines 385–387, and
`plans/detailed-usage-reporting-20261001-1610.md` lines 256–266.
The origin and scope of the old aggregate values are documented in
`/mnt/workspace/users/viperjuice/tmp/jevdrill-round21/timeout-contract-review-20261018/report.md`.

The original full confirmation remains **failed/incomplete**: 21,353 outer
tests collected, 20,963 passed, one setup error at the 300-second nested
watchdog, and 389 unrun. The retained timeline shows 29 ordered artifacts and
case 30 begun, but those artifacts do not establish passes; see
`/mnt/workspace/users/viperjuice/tmp/jevdrill-round21/nested-probe-timeout-20261018/report.md`.
The separate earlier full attempt failed on the `stall` usage case at its
20-second outer timeout; see
`/mnt/workspace/users/viperjuice/tmp/jevdrill-round21/full-runner-compat-20261018/proof-report.txt`.
The cause of timing variation is unproven. Earlier targeted, CI, and nested
passes are historical and do not certify this edited working tree or constitute
a new full-suite pass.
