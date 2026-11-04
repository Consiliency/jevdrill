DISAGREE on `Consiliency/jevdrill#1` at `6fe946126d59131a01c85d6d5ce145641f9af51b`. The cap-reduction cost gate holds, and the exact indented `Bearer`/`Basic` LF/CRLF payload is closed. Other indented Authorization and credential continuations are still submitted and retained.

## Binding

Candidate `/home/viperjuice/workspace/worktrees/jevdrill-implementation-reviewed`. HEAD `6fe946126d59131a01c85d6d5ce145641f9af51b`. Delta base `9ff504314fad47b50231a43ca6017a5071c58617`. PR base `f67ad654ff224d6b343ab366260d9184150d822f`. Manifest `/tmp/jevdrill-merge-review-20261012/round-4/source-manifest.json`, 767 files, SHA256 `54a4b6f9ea22245f0d3028748d7e1fa53554f7063ce84c6af7897e4d86342586`. `sha256sum --quiet -c` succeeded before and after the probes. Porcelain stayed 0. No source, evidence, index, or GitHub write.

## Cap reduction on `9ff5043` — closed for this seat

M1 and M2. An explicit judgment spending ceiling now stops a new injected call before preparation, reservation, and dispatch.

`Application.route` raises at `src/jevdrill/application.py:802-811` when `self.judgments is not None` and `policy["spending_ceiling"] is not None`, before `judge.judge` at line 830. `Application.discover` raises at `application.py:283-296` before `prepare_option` and `reserve_discovery_call`. Discovery merges `limits` and `policy` ceilings at `application.py:146-155`, so a ceiling on either field is enough. Built-in enforcement remains in `JevAdapter.judge` at `src/jevdrill/integrations/jev.py:135-150`. DevelopmentJudge stays pinned to `jev-1.13.0` (`src/jevdrill/integrations/development.py:114`). The request model and `utf8-bytes-upper-bound-v1` are checked on both injected paths. `docs/route-readiness.md:41` and `docs/experiment-interfaces.md:7` describe this unsupported mode. No model menu, pricing port, or empirical claim was added in the delta.

Independent stub probe, receipt `/tmp/jevdrill-r4-grok-probe-report.json` SHA256 `a9b3e17f46a6a9c5ab06aa3458eda2772484101953838a2ebeef11cf7d7916fd`:

| Case | Result | Prepare / judge | Reservation rows |
|---|---|---|---|
| Injected discovery, no ceiling | `selected_guidance` | 1 / 1 | 1 `discovery_calls` |
| Discovery policy ceiling `$0`, `$0.001`, `$1`, or EUR `$1` | `discovery_failed` | 0 / 0 | 0 |
| Discovery limits-only `$0` and `$5` | `discovery_failed` | 0 / 0 | 0 |
| Discovery model `jev-1.13.0` on a `jev-latest` adapter, or a bad counter | `discovery_failed` | 0 / 0 | 0 |
| Injected route, no ceiling | `ready` | 1 call | — |
| Route judgment ceiling `$0`, `$0.001`, `$1`, or EUR `$1` | `routing_failed` | 0 | — |
| Route wrong model, bad counter, trailing-space counter | `routing_failed` | 0 | — |
| Same route payload twice | `ready`, then `ready` | 1 call total | replay |
| Same idempotency key, ceiling added after success | `ContractError: idempotency conflict` | still 1 call | no new authorization |

The project's real `DevelopmentJudge` loopback controls in `tests/experiments/test_development_judge.py` passed in this run for allowed, unsupported model, known-but-wrong `jev-latest`, bad counter, and ceiling zero, small, funded, unknown rate, positive output rate, stale rate, and EUR. Denied cases made no HTTP call and wrote no `judgment_calls` row. Built-in route ceilings `$0` and `$1` returned `routing_failed` with 0 calls and `ready` with 1 call. Funded injected mode stays denied and unclaimed.

A route whose only ceiling is `hard_constraints.spending_ceiling = $0`, with the judgment ceiling left null, still makes one injected judge call and then returns `no_compatible_plan`. That field remains the execution-plan cap in `routing.py:112-163`. It is not the judgment-adapter ceiling this reduction removes.

## President folded-header finding — exact payload closed

M2. `Authorization: Bearer\r\n\t<token>` and the Basic, LF-plus-spaces, and multi-line Digest forms are removed. Ordinary unindented text stays.

`redact` at `src/jevdrill/context.py:15-26` now keeps ASCII space/tab continuations after LF or CRLF on an unquoted Authorization value. Confirmed clean through `collect_context` and through `Application.route` (`ready`, one judge call, token absent from the payload, the raw artifact, and the database):

- `Authorization: Bearer\r\n\tSYNTHETIC_FOLDED_SENTINEL`
- `Authorization: Basic\r\n\tSYNTHETIC_FOLDED_SENTINEL`
- `Authorization: Bearer\n  SYNTHETIC_FOLDED_SENTINEL`
- Digest `username` / `nonce` / `response` across CRLF, spaces, and a tab
- `{"name":"Authorization","value":"Bearer\r\n\tSYNTHETIC_FOLDED_SENTINEL"}`
- `api_key:\r\n\tSYNTHETIC_FOLDED_SENTINEL` when the whole value is on the continuation
- `Use basic arithmetic and explain the result.` unchanged

Discovery objective, authorized context, and description for the president payload did not submit or retain the token. The 12 discovery and route retention tests in the focused run passed. An unindented next line is still kept, which matches the stated control.

## Open blocker

M2. `docs/route-readiness.md:56` and `plans/phase-plan-v1-ROUTE.md:220-222` require credentials to be sanitized before submission and persistence. The new continuation is only the third branch of the Authorization alternative, and it requires `\r?\n` plus ASCII space or tab (`context.py:17`). Quoted values and `api_key` / `password` / `secret` / `access_token` (`context.py:19-20`) do not take that continuation. A bare CR never starts it.

These synthetic values reach the injected judge and the raw artifact. Route status is `ready`.

| Payload | Route submit | Route artifact | Discovery |
|---|---|---|---|
| `Authorization: "placeholder"\r\n\tTOKEN` | yes | yes | same `redact` |
| `Authorization: Bearer\r\tTOKEN` | yes | yes | context and description: `selected_guidance`, submitted and retained |
| `Authorization: Bearer\n\u00a0TOKEN` | yes | yes | context and description: submitted and retained |
| `Authorization: Bearer\n\vTOKEN` | yes | yes | same matcher |
| `api_key: prefix\r\n\tTOKEN` and `password: prefix\r\n\tTOKEN` | yes | yes | same matcher |

`_sanitize` (`application.py:68-75`) is the route and discovery boundary. The route artifact is the sanitized task (`application.py:951-955`). Discovery retention uses the sanitized objective, context, and description (`application.py:218-230`). The token is the literal `SYNTHETIC_FOLDED_SENTINEL`.

Minimal repair: one continuation, `(?:\r\n|\n|\r)[^\S\r\n]+[^\r\n]*`, applied after quoted, single-quoted, and bare values on every credential alternative. Cover the quoted-then-fold, bare-CR, NBSP, and split `api_key` forms in the existing route and discovery submission and raw-retention checks. A blank line still ends the header; that case can stay.

## Other objections

Round-2 authority, quoted single-line credentials, worker scrub, imported tombstones, downstream controls, and duration sum were closed at `d20819f` and are not reopened here. I did not re-execute them. Portable v1 still omits the experiment ledger and raw discovery artifacts. That remains a documented fail-closed limit. Historical replay is preserved. F6/F7/D2/D4/D6 were not used to widen scope.

## Verification and limits

This seat ran 78 focused tests, 0 failures, 0 errors, 0 skips, 15.289s. JUnit `/tmp/jevdrill-r4-grok-focused.xml` SHA256 `90ef44d7e24af60bf3c9b43c148cdebe664f7524089ab19adf1feaa8c91b5d0d`. `BAML_CLI` was the pinned route compiler and `BAML_AGENT_SKILL_CHECK=off`. That run includes the real loopback `DevelopmentJudge` matrix and the new fold controls.

I inspected the parent file `/tmp/jevdrill-merge-r4-full.xml` SHA256 `b8321f70f11480fcaf0b715e877ab86bc3685d6346f77098712eb26a87eb515c`: 952 tests, 0 failures, 0 errors, 0 skips, 421.263s. I did not execute that suite. It does not contain the bypasses above. I did not read CI, so current-head CI stays pending. I did not rerun ruff or mypy.

No live provider, secret file, holdout, study, grant, or deployment. The attachment-only Application request I built was schema-invalid, so attachment coverage for the president payload is `collect_context` plus the shared `_sanitize` path. This seat is not the president.

DISAGREE
