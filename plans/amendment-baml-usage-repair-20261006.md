# BAML partial-usage repair amendment

## Authority and scope

The owner requested continuation and explicitly selected a pinned local BAML TypeSafe client patch on 2026-10-06. Preserve upstream attribution and parity tests; remove the patch when upstream supports partial counts. This amendment extends package B of `detailed-pre-gepa-repairs-20261005-1336.md`. It does not authorize live calls, increase the $2 guard, change suitability semantics, or close roadmap gates.

## Changes

- Vendor the TypeSafe BAML client from `baml-language-0.20.1` under `baml_src/ns_typesafe_patch/`, with license, original digests and documented modifications. Preserve request construction and Boolean decoding.
- Add an internal observation callback before answer decoding. Preserve partial counters and sanitize malformed counters. Keep payloads and credentials out of observations. Keep the compiler and bridge pinned.
- Update `baml_src/jev.baml`, its generated SDK, `integrations/jev.py`, `telemetry.py`, `contracts.py` and `application.py` only for observation projection, failure preservation and cache accounting. Existing public schemas and vocabulary remain unchanged.
- Extend boundary, integration, privacy and application tests. Update the generated-file checker for nested BAML source paths and update `docs/contracts.md` and `docs/route-interfaces.md`.
- Ship upstream licensing and attribution in `src/jevdrill/BAML_TYPESAFE_LICENSE` and `BAML_TYPESAFE_NOTICE.md`, so wheel and source distributions include them.
- Preserve all existing evidence. New private work goes under `.phase-loop/runs/BAML-usage-repair-20261006/`; new public evidence goes under `evidence/EXPERIMENT/baml-usage-repair-20261006/`.
- Update `evidence/ROADMAP/latest-study.json` to reference this repair and retain the complete previous study record. Existing phase verdicts remain unchanged.

## Verification and acceptance

Require request-body and Boolean parity at scores 0, 0.49, 0.5, 0.51 and 1; exactly one request; zero remains zero; partial and absent counts remain unknown; malformed/conflicting counts cannot become known. Cover observer delivery before malformed answers, timeout/cancellation, injected adapters, cached reuse and replay. Run targeted tests, pinned generation comparison, vocabulary/import checks, lint and the full suite. Package B remains blocked until these checks and the original package B acceptance requirements pass.

## Budget preparation

The frozen maximum reservation permits one case across five arms: five generations and four judgments, at most $0.855004000 new reservation, plus $0.845159775 inherited commitments. This is an execution smoke test, not suitability calibration or quality acceptance. Re-read authoritative ledgers and obtain live execution authority before dispatch. Preserve the original 36-case proposal and its budget failure.
