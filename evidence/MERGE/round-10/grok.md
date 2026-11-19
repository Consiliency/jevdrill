# Round-10 Grok seat — Consiliency/jevdrill#1

Verdict: **DISAGREE** at `392f2234f397aaee0725c6b37c9ef42c15587bf7`.

Unresolved computed literal records that contain no string constant are submitted on all six context boundaries. The published rule requires those records to be rejected without executing the expression. Eight shapes produced 48 judge HTTP submissions and 40 raw artifacts. OpenPGP armor also left the synthetic sentinel on the wire; that stays a suggestion under the PEM delimiter the contract implements.

This seat is a board seat. The round-5 `BLOCK_MERGE` stays in force until a separate president rules after all four fresh seats finish. Software checks are not empirical acceptance.

## Binding

Actual root: `/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed`. Composer checkout was not reviewed.

| Check | Before probes | After probes |
| --- | --- | --- |
| HEAD | `392f2234f397aaee0725c6b37c9ef42c15587bf7` | same |
| `git status --porcelain` | empty | empty |
| Tracked files | 801 | 801 |
| `sha256sum --quiet -c` `source-manifest.sha256` | exit 0 | exit 0 |

Manifest JSON SHA256 `d99836fab215e0d0a96f37e152d2597ee35ea394d02bf5d587bc293d86f877c2`. Review packet `review-brief-verified.txt` is 339414 bytes, 2659 lines, SHA256 `02a38cb933db536db5e28e839c95d6b0c03e514084814cded0820e8a1d855014`. The first round-10 verified header is the binding. Later packet sections stay attributed to their own heads. Imported module: `src/jevdrill/__init__.py` in this root. SDK tracked files: 147, including `src/baml_sdk/typesafe_patch`.

Seat evidence: `/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round10-20261015/reviews/grok/seat-392f223/`.

| File | SHA256 |
| --- | --- |
| `probe.py` | `464e4ba52b811ecd953dda1cbcb569ed5f6aa88c24415cd81be54b46d7d53cd9` |
| `evidence.json` | `fe86aff614b05bd8161458d6bc53a3e6e8d8b33b86523b63541786c993f97631` |
| `redact.json` | `8ece3843458ea7a7b5e08ca161dce15d95b140813d870769912588a94b483375` |
| `loopback.json` | `a3ff0b04f79f190cb3a9aef410ba452e246e4c907cded4832cde1a1c192131a6` |
| `narrow.xml` | `36fdbf26a0bbc91ca3738b74f517258f15e39a43e994a7b9749bdfffce8299db` |

Sentinel: `SYNTHETIC_R10_GROK_SENTINEL`. Fresh synthetic allowances, ephemeral `127.0.0.1` DevelopmentJudge, separate SQLite per case. No GitHub writes, no full suite, no native-host rerun, no `verify_*` `main()`.

## Blocker

**Unresolved computed literal records with no string constant are sent and retained.**

Invariant: `docs/route-readiness.md:78-80` — constant string addition and expression-free formatted fragments are inspected without executing supplied code; unresolved computed literal records reject. Falsifier: `plans/phase-plan-v1-ROUTE.md:410` EC-ROUTE-4, a retained or sent excluded sentinel.

Source: `src/jevdrill/context.py:337-349`. The walk treats only `BinOp`, `JoinedStr`, and `Call`. It marks the record unresolved only when that node is a `JoinedStr` or the subtree contains a `Constant` `str` or `bytes`. `chr(97)` arguments are integers. `header_name()` and `prefix + suffix` contain no string constant. `header_name[:]` is a `Subscript`, which the walk does not inspect. The quoted-label fallback at `context.py:447-455` never sees the word `api_key`. The integer literals `97,112,105,95,107,101,121` spell `api_key`; the sanitizer returns the source unchanged.

`''.join(('api_', 'key'))`, `f"{'api_'}{'key'}"`, `f'{header_name}'`, and `'api_' + chr(107) + 'ey'` do reject, because those trees contain a string constant or a `JoinedStr`. The repaired matrix covers that subset. It does not cover the eight shapes below.

Each shape was submitted through route task, route attachment, discovery objective, authorized context, description, and discovery attachment. Each of the six boundaries made one HTTP request and one judgment reservation. The sentinel was in the request body. Raw artifacts kept it on five boundaries. Route attachments are on the wire and absent from raw-task artifacts. The judgment SQLite files did not contain the sentinel. Route returned `ready`. Discovery objective later returned `discovery_failed` after the request had already been made. Rejections elsewhere in this probe had zero requests, artifacts, and reservations.

| Case | Input | HTTP | Raw |
| --- | --- | --- | --- |
| `chr-dict` | `{'name': chr(97)+chr(112)+chr(105)+chr(95)+chr(107)+chr(101)+chr(121), 'value': SENTINEL}` | 6 | 5 |
| `chr-assign` | `headers[chr(97)+...+chr(121)] = 'SENTINEL'` | 6 | 5 |
| `chr-pair` | `[[chr(97)+...+chr(121), 'SENTINEL']]` | 6 | 5 |
| `func-dict` | `{'name': header_name(), 'value': 'SENTINEL'}` | 6 | 5 |
| `func-assign` | `headers[header_name()] = 'SENTINEL'` | 6 | 5 |
| `add-names` | `{'name': prefix + suffix, 'value': 'SENTINEL'}` | 6 | 5 |
| `add-names-assign` | `headers[prefix + suffix] = 'SENTINEL'` | 6 | 5 |
| `slice-name` | `{'name': header_name[:], 'value': 'SENTINEL'}` | 6 | 5 |

Minimum repair: in that walk, a `BinOp`, `JoinedStr`, `Call`, or `Subscript` inside a dict, list, tuple, or assignment target whose `_literal_string` result is `None` sets unresolved even when no string constant is present. Do not execute the node. Keep constant addition, expression-free formatted fragments, whole-statement masking of resolved sensitive targets, and noncredential `Content-Type` additions.

## Closed on this head

Round-9 objections, re-executed here:

- Dash-only YAML, space and tab indent, rejects `unsupported structured credential sequence` on all six boundaries. Zero HTTP, artifacts, and reservations.
- Expression-free adjacent f-string `{'name': 'Author' f'ization', ...}` rejects `unsupported concatenated literal credential` on all six boundaries. Zero side effects. Replacement-field `f"{'api_'}{'key'}"` and `f'{header_name}'` reject `unsupported computed literal record` at `redact()`.
- Bare-CR `header: Authorization\rpayload: SENTINEL` is re-serialized with both values `[redacted]`. Sentinel absent from all six wires and raw artifacts.
- Standalone Basic with a NEL continuation returns `[redacted]\x85Ordinary context`. Sentinel absent. Ordinary text kept on every boundary.
- `headers['Author'+'ization'] = SENTINEL` followed by an ordinary line returns `[redacted]\nOrdinary context` on every boundary. `headers['Content'+'-Type'] = 'application/json'` stays usable.
- Complete PEM block redacts to `[redacted]` with the sentinel absent on every boundary. YAML association `header` / `Authorization` / `payload` redacts all three values at `redact()`.
- Incomplete `-----BEGIN PRIVATE KEY-----\n` repeated 1000/2000/4000/5000 times raises `incomplete private-key block` in 0.021 / 0.034 / 0.063 / 0.077 ms CPU. CLI of the 5000-opener payload with `--remaining-budget-ms 5000` and judgments disabled: 0.305 s, exit 2, status `invalid`, empty stderr. Ordinary 20k `a`: 0.299 s, `ready`. `x\\\n` × 20000: 0.325 s, `no_compatible_plan`. `{` × 20000: 0.589 s, `invalid`. The five-second deadline is unchanged.

Historical disclosures, the omitted-dash bug, the private-key deadline miss, Windows failures and timeouts, and the colliding-ID partial proof stay historical. They are not rewritten as current passes.

## Presidential requirements

Round-5 president, still the binding ruling, applied to this head:

1. One credential-label predicate after trim, case, and separators. `_credential_label` is still that predicate. Computed records that never reach it are the blocker above.
2. Decode without dropping members, and do not restore original bytes when duplicates exist. The privacy suite that encodes this passed. This seat did not find a new duplicate-key leak.
3. Sibling masking inside a decoded object or array. Confirmed for the constant-addition target, the single `password =` assignment, the CR mapping, and the PEM-plus-YAML association. The chr/call/name records do not mask the sibling.
4. Labeled free text keeps indented continuations and the ordinary unindented next line. Confirmed for the assignment and the NEL Basic fold.
5. YAML, Python literals, and code assignments are handled or fail closed before submission and retention. Fail-closed is missed for the eight shapes in the blocker.
6. Generated labels, formats, and six boundaries must keep the secret off the wire and out of retained bytes, while ordinary text survives. The published matrix does this. The eight unlisted shapes do not.

Also confirmed in source and by the narrow tests: an injected judge with `spending_ceiling` set raises `unsupported judgment profile or spending bound` at `application.py:813-822` before `judge.judge`. Discovery raises `discovery judgment not authorized` at `application.py:290-303` before `reserve_discovery_call`. Portable import inserts `experiment_recovery_blocks` at `storage.py:1244`, and admission refuses a blocked scope at `experiments.py:203-204`. Empty provider allowlists, funded injected pricing, and portable omission of the experiment ledger remain the documented limits from prior rounds. Unratified roadmap items do not expand this review. Four fresh agreements do not exist. This dissent does not replace the president.

## Independent checks

- `candidate1/full.xml` SHA256 `a332f36e222ee796c379964ead63235fee34678894ac4aed8feee77893da3be8`: 6118 tests, 0 failures, 0 errors, 0 skips. Not rerun.
- Loopback receipt SHA256 `087443cddedf2e99c772de804a45238c5eae139e24136be7aeb7c3c63f158982`. Inputs `450d0db81ec82451365fb720053b8ca40f9ad6efddd30e371e06b0b72f0bbbea`. Reviewer inputs `b169f96cd1da312ada34c998aba914fa952b0f0b592daebf32888f17dced521a`.
- `reduce_manifests` on the three route manifests and three contract manifests returned no errors. Route digest `ce3f6ab5ac9ea09a41b84316f3f48311bb8f1173d5658ebfb2534c023f22580f`. Contract digest `11721f6f08c6a2fc58fa060e95ecbe6f4d7ebc5e1ac43032e49c10e166325083`. Route: Darwin 5620 in 226.337 s, cold CLI 0.482 s; Linux 5620 in 176.636 s, cold CLI 0.606 s; Windows 5620 in 224.309 s, cold CLI 0.733 s. Failures, errors, and skips are zero. `proof_cost_target_exceeded` is false. Contract: 322 tests and 0 skips on Darwin, Linux, and Windows.
- `ci-binding.json` head is this HEAD. Fourteen check instances, nine distinct workflow-and-name pairs, all `SUCCESS`, including both Contract conformance runs `38833315985` and `38833310685` and ROUTE run `38833316151` attempt 1. Read from the binding file. GitHub was not queried again.
- Narrow pytest, seat `--basetemp` and JUnit, existing `.venv`: 3964 passed, 0 failed, 0 errors, 0 skipped, 44.63 s. That run covered context and discovery privacy, the four CLI deadline cases, provider allowlist, injected ceiling, recorded replay, idempotency conflict, and reservation crash recovery. A green matrix does not contain the chr/call/name/slice inputs, so it does not answer the blocker.

## Suggestions

- OpenPGP armor `-----BEGIN PGP PRIVATE KEY BLOCK-----` / `END` with the sentinel between them is returned unchanged. The delimiter at `context.py:44-45` requires `PRIVATE KEY-----`, and `BLOCK` sits between `KEY` and the dashes. Loopback: 6 HTTP, 5 raw artifacts, 0 SQLite copies, same boundary split as the blocker. PEM blocks that end in `PRIVATE KEY-----` redact. This seat leaves OpenPGP armor as a suggestion, in the same class as colonless text, because the implemented delimiter and the round-10 PEM repair describe those PEM blocks. `docs/jevdrill-spec.md:394` still says not to collect secrets; a president can widen the delimiter.
- `Authorization Bearer SENTINEL` and `set_password("SENTINEL")` still come back from `redact()` unchanged. They were not put through HTTP again in this round. Prior seats left them as suggestions. Zero-width labels, fullwidth letters, unquoted tuples, and split one-field YAML maps were not re-executed.

## Limits

The full 6118 suite, native hosts, and the companion were not rerun. Historical CR and NEL matrices were not re-looped for every label; one CR mapping and one NEL Basic fold were, and the privacy files that generate the published matrix passed. No real provider, study, grant, holdout, or secret was touched. The stopped study and the dirty composer worktree were left alone.

DISAGREE
