DISAGREE on `Consiliency/jevdrill#1` at frozen head `d20819f88977d6aa78c371287ca8ee8cb2ab67ea`. The six Round 2 repairs hold under this seat's controls. Two authorization holes still violate M1 and M2: an injected judge spends past the request ceiling, and some credential spellings are still submitted and retained.

## Open blockers

### 1. Injected task and discovery judges ignore the request spending ceiling

M1 and M2. `plans/phase-plan-v1-ROUTE.md` lines 204–212 require a configured ceiling to be rejected before any HTTP request when the adapter cannot enforce it, and they require verified input pricing plus a zero output rate before a ceiling can authorize spend. `docs/route-readiness.md` lines 61–63 and `docs/jevdrill-spec.md` line 196 say the same: exhaustion returns an explicit inability, and a ceiling is not optional once it is set. Round 2 closed the provider allowlist on the injected path and left this cost check only on the built-in adapter.

`Application.route` selects `self.judgments` at `src/jevdrill/application.py:793` and calls `judge.judge` at line 813. `JevAdapter.judge` enforces the ceiling at `src/jevdrill/integrations/jev.py:135–150`. `DevelopmentJudge.judge` (`src/jevdrill/integrations/development.py:398–406`) never receives the request policy. It reserves its own 2753 microusd and then performs HTTP. `Application.discover` gates enabled, cloud, provider, and hard output at `application.py:283–289` and does not consult the ceiling. `DevelopmentJudge.prepare_option` (`development.py:219–227`) returns a fixed `reserved_spend` of `"0.002753"`. `SQLiteStorage.reserve_discovery_call` (`storage.py:1722–1728`) compares that reported figure with the ceiling, so a ceiling above the hardcoded allowance proceeds to `observe_option`.

Repro, loopback only, receipt `/tmp/jevdrill-r3-grok-ceiling-repro/receipt.json` (sha256 `74fc11f163e499a777aed33d8d7aadc2372f4301a317d80180233b42b7c7c7d1`):

| Case | Result | HTTP | Reserved |
|---|---|---|---|
| Injected route, ceiling `$0`, input rate `$1`, output rate `0` | `ready` | 1 | 2753 microusd |
| Injected route, ceiling `$0.001` (below that reservation), same rates | `ready` | 1 | 2753 |
| Injected route, ceiling `$0`, rates missing | `ready` | 1 | 2753 |
| Built-in route, those three policies, model `jev-latest` | `routing_failed` | 0 | — |
| Injected discovery, ceiling `$0.01`, input rate `$1` | `selected_guidance` | 1 | 2753 |
| Built-in discovery, same policy | `discovery_failed` | 0 | — |
| Injected discovery, ceiling `$1`, rates missing | `selected_guidance` | 1 | 2753 |
| Injected discovery, ceiling `$1`, output rate `$0.01` | `selected_guidance` | 1 | 2753 |
| Built-in discovery, both of those policies | `discovery_failed` | 0 | — |
| Injected discovery, ceiling `$0`, priced rate `$1` | `discovery_failed` | 0 | 0 |

The zero discovery ceiling stops only because `0.002753 > 0`. The same adapter still dispatches when verified pricing cannot support the ceiling.

Minimal repair: before `prepare_option`, `observe_option`, and `judge.judge`, reject in `Application` unless the selected adapter has a fresh verified input rate, a zero output rate, and a conservative estimate no higher than the ceiling. Missing rates, a positive output rate, a stale card, or an adapter reservation the request did not price are unsupported ceilings and must fail before HTTP. Add loopback controls for zero, insufficient, missing-rate, positive-output-rate, and funded ceilings on both injected adapters. A funded injected route with ceiling `$1` and a tiny rate did dispatch once, which is the allowed control.

### 2. Split and folded credentials are still submitted and retained

M2, plus `docs/route-readiness.md` lines 54–56 and `plans/phase-plan-v1-ROUTE.md` lines 220–222: credentials are sanitized before submission and persistence. The redactor at `src/jevdrill/context.py:15–20` only matches an authorization or secret key and its value on one span. Through `Application.route` with raw retention on, these task strings stayed intact in the injected judge payload and in the raw artifact:

- `{"name":"Authorization","value":"Bearer SYNTHETIC_SENTINEL"}`
- `Authorization: >` followed by a newline and `Bearer SYNTHETIC_SENTINEL`
- a bare `Bearer SYNTHETIC_SENTINEL`

Each returned `ready`. The same probe redacted `Authorization: Bearer SYNTHETIC_SENTINEL` and `api_key: SYNTHETIC_SENTINEL extra`.

Minimal repair: redact bearer and basic token values when the scheme is split from the header name, including JSON name/value headers and folded header values, and cover those forms with the existing Application submission and raw-retention checks.

Unquoted multi-word secrets are a residual of the same regex (`[^\s,;}]+` stops at whitespace). This seat did not run a spaced unquoted secret through `Application`, so that remains a suggestion on the same repair.

## Round 2 blockers

All six are closed on this head.

1. Discovery authority. `test_application_checks_discovery_authority_before_actual_adapter_calls` passed for allowed, `local_only`, allowlist, disabled, cloud, spoofed provider, and hard output. Denied cases made no loopback request. A non-null hard output ceiling rejecting before dispatch is the plan's fail-closed rule.
2. Quoted credentials. All six route retention cases and four context cases passed, including quoted Bearer, JSON `api_key`, Digest, and a single-quoted password with spaces.
3. Worker bytes. `test_deleting_completed_experiment_scrubs_terminal_worker_content` passed for direct deletion. The runner sets `secure_delete` and `VACUUM` after the scrub.
4. Imported tombstones. The same test passed with `imported=True`. Direct delete and import share `_purge_task`. Portable v1 still has no experiment ledger: import inserts `experiment_recovery_blocks` (`storage.py:1244`) and admit refuses with `experiment_recovery_authority_unreconciled` (`experiments.py:203`). That restriction stays explicit. This seat did not re-run the portable admission control.
5. Downstream required controls. `test_downstream_commands_cover_phase_controls_and_bind_extra_paths` passed for HOST, LEARN, and EXPERIMENT. The parameterized reducer accepts `control[0-None]` and still rejects a missing control. Parent collect-only file `/tmp/jevdrill-merge-review-20261012/round-3/downstream-collection-final.json` (sha256 `933a3992ca2e131bdd2ee096ccef14be7fdb61a0219759899bc5a1266368a4b3`) records head `d20819f`, manifest `5c02541e…d8db`, and 448 HOST / 494 LEARN / 697 EXPERIMENT with empty `missing_required_controls`. This seat did not call `collect()` because HOST collect writes `evidence/HOST/history`.
6. Overhead sum. `objective_duration` at `scripts/verify_discovery_calibration.py:456–457` is the producer and both validators (`:464`, `:913`, `:1473`). Both duration cases passed, including `[0.0, 0.1, 0.7, 1.0]`. Omission still uses `<`. No tolerance was added.

`docs/route-readiness.md` line 49 still records that portable v1 keeps discovery metadata and omits raw discovery artifacts. That is a stated limitation, and it is consistent with the metadata lineage. It is not a waiver of the two open blockers.

## Verification and limits

Review root `/home/viperjuice/workspace/worktrees/jevdrill-implementation-reviewed`. After the probes: HEAD `d20819f88977d6aa78c371287ca8ee8cb2ab67ea`, porcelain 0, `sha256sum --quiet -c /tmp/jevdrill-merge-review-20261012/round-3/source-manifest.sha256` succeeded for the 753-file manifest `5c02541e79f37e0353f41bab4e06dd7d0369be8d20628c14636f58ad8106d8db`. No source, index, evidence, or GitHub write.

This seat's repair run is `/tmp/jevdrill-r3-grok-controls.xml` (sha256 `52d22257f20aedfa3722d2b248c0c18e1cbffb91784d8652e5601319134a0a86`): 25 passed, 0 failed, 0 skipped, 5.80s, with `BAML_CLI` pointed at the pinned route compiler and `BAML_AGENT_SKILL_CHECK=off`.

Parent frozen suite `/tmp/jevdrill-merge-r3-frozen-full.xml` hashes to `5e5176b0621034275c0fbc60e26a21d7a1a7997506fdb76f6401692b0bfad7ab` and contains 897 tests, 0 failures, 0 errors, 0 skipped. This seat did not re-run it. That suite has no injected-ceiling control, so the green count does not close blocker 1.

Current-head GitHub checks, read with `gh run view`, are success on `d20819f`: Contract conformance `38324059889` (ubuntu, macos, windows, reduce), ROUTE verification `38324059803` (Darwin, Windows, Linux, reduce), and EXPERIMENT offline boundaries `38324059791`. Nine jobs, all success. These do not exercise the injected ceiling.

Built-in discovery `observe_option` was wrapped to raise before any provider call. The failing built-in cases never reached it. Built-in route failures happen inside `JevAdapter.judge` before `JudgeCandidate`. No live provider, secret file, holdout, study, grant, or deployment was used. F6/F7/D2/D4/D6 were not used to widen scope. This seat is not the president, and no further seat was launched.

DISAGREE
