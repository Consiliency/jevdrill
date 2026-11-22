# ROUTE readiness

The ROUTE verifier selects its phase-owned tests explicitly, including every required executed control. The HOST, LEARN and EXPERIMENT collectors are not on `main` (see [roadmap status](roadmap-status.md)). When they land, they add their own required test suites to this selection through `extra_test_paths`, and their reducers bind those commands and assertions. The HOST conformance tests against the installed host integration belong to those collectors and are not on `main` either. One LEARN test on `main` needs that installed integration (`tests/application/test_learning.py::test_installed_discovery_host_tasks_reports_analysis_and_entered_denials`); the `Unit tests` workflow deselects it.

ROUTE implements discovery, durable task routing/reporting and replay on the
strict BAML boundary. Discovery advances its own questions through catalog
metadata, records uncertainty and returns admitted instructions. A successful
stored discovery can feed each independently constrained task through route-v2.
The application does not decompose objectives or launch executors; HOST must be
replanned against the interfaces in `docs/route-interfaces.md`.

The current verdict is the `route-verification` artifact of the ROUTE verification
workflow for the commit under test. A local run writes the same report to
`evidence/ROUTE/verification.json`, which is not committed. Acceptance requires
all seven EC-ROUTE criteria and IF-0-VC-2, matching current-source native
Linux/macOS/Windows Python 3.14 manifests, pinned generation, shared fixtures,
privacy/crash controls, installed-package checks and the five-second cold CLI
boundary. The reducer checks executed test identities and outcomes as well as
command, source and assertion digests. Old four-criterion reports and skipped or
missing controls fail. Earlier reports stay with the record of Consiliency/jevdrill#1
and are not on `main`.

```sh
BAML_CLI=/path/to/baml-cli uv run python scripts/verify_route_phase.py --local-only
uv run python scripts/verify_route_phase.py --reduce-only
```

Local-only collects one native platform and does not close the full matrix.
Collection is bounded to ten minutes; reports flag runs above the five-minute
proof-cost target. Neither allowance changes the product deadline.

The CLI accepts one JSON document on stdin and produces one JSON response on
stdout. Use `--storage PATH` and the host's spawn-inclusive
`--remaining-budget-ms N`. ROUTE's commands are `discover`, `route`, `report`,
`inspect`, `delete`, `inspect-discovery` and `delete-discovery`. Exit codes are
0 handled response, 2 invalid input/version, 3 idempotency conflict and
4 infrastructure/deadline failure. Native Windows verification uses the installed
interpreter with `-m jevdrill.cli`, following the existing unsigned-launcher
configuration; it does not change security policy.

Request privacy and provider authority apply before each built-in or injected discovery adapter call.

Requests needing a new injected task or discovery judgment with an explicit spending ceiling fail before preparation or dispatch; that adapter mode is unsupported. Built-in adapters retain their verified pricing checks. The request model must match the configured adapter model, and the supported token counter is `utf8-bytes-upper-bound-v1`. DevelopmentJudge is pinned to `jev-1.13.0`; built-in and ordinary synthetic observers use `jev-latest`.

Discovery reserves provider work durably before dispatch. Each key has its own
immutable allowance; interrupted same-key recovery makes no new provider call.
It atomically commits supported partial guidance or interrupted failure.
Terminal observations are audit-only. Objective tombstones span producers in
one project/workspace and invalidate all attempts, retries, replay and linked
route commits. Existing task records keep their independent lifecycle.

Raw objective/context/description retention is opt-in. Retained discovery content uses the ordinary artifact lifecycle, keyed by its discovery ID: archive prompt, encrypted archival after the grace period, and expiry. Seeds, questions and replay traces remain metadata-only; retries do not recreate expired raw content. Objective deletion removes the associated artifacts.

Portable v1 recovery preserves successful discovery metadata but omits raw discovery artifacts, whose objective-to-content lifecycle mapping is local. Local encrypted archival and restore remain available before expiry; portable recovery does not revive deleted objective content.

Metadata replay validates
questions, answers, FIFO transitions, budget deltas and deterministic selection
from recorded admission/compatibility/context facts without regenerating prompts
or using a live catalog. Excluded attachments are left out before submission and
persistence. Selected catalog instructions remain local except
for explicitly returned guidance. No hidden reasoning is retained.

What the credential check refuses, and what it does not detect, is described in one place: [the credential-check contract](sanitization-contract.md).

The pinned TypeSafe patch and attribution are preserved. Missing usage/prices
remain unknown; conservative UTF-8 packing is a bound, not measured usage.
Output planning reservations do not enforce provider output. A requested hard
output ceiling rejects before dispatch. Spending ceilings require verified input
pricing and zero output rate. Task spending/token ceilings require verified
whole-run execution limits and later host enforcement; planning estimates alone
cannot establish compliance.

Evidence uses synthetic public inventories, caller flows and loopback BAML
judgments. It establishes software behavior, not live latency, model quality,
professional suitability, production companion readiness or policy promotion.
Replan HOST, then LEARN/EXPERIMENT/PREPARE in dependency order. Independent live
quality evidence and real decomposition remain downstream work.

The credential check also runs on supplied objective descriptions and recorded learning context before assessment and history retention, and on every mapping key. A refused analysis request stores nothing. Routing persists monotonic learning restrictions before committing a replayable decision, so a post-commit crash cannot drop an opt-out. Storage version 4 preserves one learning dependency per task and objective; migration retains known version-3 rows, and deletion also consults retained context lineage to invalidate dependencies omitted by the earlier key. This does not claim to reconstruct already-lost historical evidence.
