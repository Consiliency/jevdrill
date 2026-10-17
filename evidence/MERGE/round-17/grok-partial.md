# Round-17 Grok board seat — Consiliency/jevdrill#1

**DISAGREE.** Do not merge at `a903353bcb394779fb528a6ac9fa61717664dfed`.

Two current M2 blockers remain. A YAML double-quoted backslash-newline continuation joins a credential label in mixed prose, in a JSON string, and in a JSON log object, and `redact` returns that original text. A same-line explicit key whose value indicator sits on that same line is skipped when YAML cannot compose the document, including vertical tab, form feed, tab, and ordinary space after prose. Both families reach a local DevelopmentJudge. Route task text is also retained. Discovery retains the unsanitized text on the objective, authorized context, attachment, and resource description. This seat is not the separate president and does not authorize a merge. The round-5 `BLOCK_MERGE` stays binding until four fresh usable AGREE reviews and a new separate tools-enabled presidential ruling on this unchanged source.

Sentinels used here: `SYNTHETIC_R17_GROK_SENTINEL` on direct `redact`, `SYNTHETIC_R17_GROK_HTTP_SENTINEL` on HTTP. No supplied call was executed.

## Binding

Reviewed root for every repository operation: `/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed`, branch `codex/implementation-reviewed`. The composer checkout was not reviewed.

| Check | Before probes | After this report’s binding |
| --- | --- | --- |
| HEAD | `a903353bcb394779fb528a6ac9fa61717664dfed` | same |
| `git status --porcelain=v1 -uall` | empty | 0 lines |
| Tracked files | 840 | `sha256sum --quiet -c` of `candidate1/source-manifest.sha256` exit 0 from this root |
| Manifest JSON SHA256 | `83f63a466ef4e9bbc0cd3bf4775644dfc7995f026ab8c3ede6b4ad6d472e106f` | same |
| SDK files under `src/baml_sdk` | 147 | 147 |

Packet `review-brief-verified.txt`: 1330098 bytes, 9878 lines, SHA256 `8705eb1aff071ff140a90d74a7ec7fd6bd520eed7b2f2aa15a64cae4a15cf935`. The first round-17 header and current `verification.json` govern. Nested heads, votes, and failures keep their original scope.

Seat directory, outside the source tree: `/home/viperjuice/tmp/jevdrill-round17-reviews/grok/seat-20261017T041204Z-2886571/`. Interpreter: the candidate `.venv/bin/python`, without resolving the symlink. `PYTHONDONTWRITEBYTECODE=1`. Pytest cache was not used. No source, index, tracked evidence, companion, composer checkout, or GitHub content was edited.

## Reading ledger

The packet was read with the file tool in untruncated numbered chunks across this review. A hash or a search was not treated as a substitute for those narrative ranges. Line 9487 is 190007 characters of machine JSON. It was parsed programmatically in this review as the initial proof audit (`completion_status` `FAILED_INCOMPLETE_FULL_PROOF`, scope “no board vote”). It was not displayed line by line. Lines 8448–8690 are the remainder of the historical round-16 verification JSON after its opening counts; the narrative reports that restate those counts were read, and every nested native command string in that JSON span was not separately displayed.

Inclusive ranges read as narrative in this review:

| Lines | What that span is |
| --- | --- |
| 1–739 | Round-17 header, current instructions, nested rounds through the start of later history |
| 740–1019 | Nested repair text and early seat reports |
| 1020–4927 | Rounds 6–12 reports and responses, including round-11 Astra’s provider failure and round-12’s four DISAGREE reports |
| 4928–8447 | End of round-12 Grok, rounds 13–15 complete reports, round-15 Astra provider failure and partial diagnostic, round-16 response, and the opening of the round-16 machine facts |
| 8691–9139 | Round-16 correctness AGREE, Astra, alternative through DISAGREE, and the start of round-16 Grok |
| 9140–9407 | Rest of round-16 Grok and the round-17 response opening |
| 9408–9486 | Rest of the round-17 response, diff note, development note, initial-failure and interruption records, relocation record, and the path header for the giant audit line |
| 9488–9878 | Current verified facts for `a903353`, including the preserved initial failure, the interrupted first retry, and the HTTP relocation record |

Separately read in full from the frozen tree: `evidence/MERGE/round-17/responses.md` (89 lines) and `evidence/MERGE/round-5/president.md` (166 lines). Current `src/jevdrill/context.py` member-validation and assignment paths, `application.py` sanitize/dispatch/retention lines, and `docs/route-readiness.md` lines 56–124 were read on this head. This seat did not line-audit all 840 files and did not read other seats’ current-round drafts.

## Current blockers

Shared invariants: sanitization before submission or persistence (`plans/phase-plan-v1-ROUTE.md:220`); EC-ROUTE-4 is falsified by a sent or retained excluded sentinel (`plans/phase-plan-v1-ROUTE.md:410`); quoted records are checked with YAML escapes decoded at their original placements (`docs/route-readiness.md:91-92`); recognized continuation whitespace is normalized only in the validation view (`docs/route-readiness.md:97`); unsupported mixed and computed records fail before judgment and raw retention (`docs/route-readiness.md:65-90`). The shared sanitizer is `application.py:68`. Discovery stages the raw objective state at `application.py:225-241` before the judge loop. Route calls `judge.judge` at `application.py:841` and stages route raw task text at `application.py:962-970`.

`S` below is the HTTP sentinel. Each leak was returned with that sentinel by `redact` and then submitted. Route attachments are on the wire and absent from the route raw-task artifact. Discovery `discovery_failed` after transmission does not undo the request or the raw artifact. SQLite files in these runs did not contain the sentinel. The credential lambda returned a synthetic inline value and was not printed.

### GR17-A. A double-quoted backslash-newline joins the label, then the original bytes return

```text
Ordinary context.
name: "Author\
ization"
value: S
```

The same join leaks at `redact` for `password` (`"pass\<newline>word"`), `api_key`, `secret`, and `access_token`. `json.dumps` of the prose document (`json-cont`) and `json.dumps({"log": prose})` (`log-cont`) leak. The pure YAML document of the same mapping is changed and the sentinel is absent (`cont-label-pure`, HTTP `cont-pure`). A vertical tab inside the letters of a quoted word is a separate direct result (`vt-inside-quote`). That word is not the contiguous label `authorization`, so it is not this blocker.

Mechanism on this head:

- `context.py:461-468` rewrites each physical line break to the two characters `\` and `n` before `yaml.scan`. The decoded token is therefore not the joined label `Authorization`.
- `context.py:477-480` returns the original quoted text when the resulting literal is not a credential.
- `context.py:244-253` JSON-decodes a quoted scalar and calls `redact(decoded)` when the decoded string contains a line break. A return that still contains the secret does not raise, and the caller ignores that return.
- Pure YAML composition reaches `_redact_node`, sees the decoded label, and masks the sibling. Mixed prose never gets that compose, so the original bytes survive.

HTTP, fake-inline `DevelopmentJudge` on `127.0.0.1`, fresh synthetic allowance and database per case. Route rows are from `probes/http-receipt.json`. Discovery dispatch rows are from `probes/discovery-wire-receipt.json` only. The earlier discovery rows in `http-receipt.json` and `discovery-receipt.json` replaced the fixture objective id or kept an allowance that `DevelopmentJudge.prepare_option` cannot reserve (`input_tokens` 65536, `output_tokens` 0). Those two receipts have `http_requests` 0 on the positive control. They are harness failures. They are not a privacy result and they are not cited as wire disclosure. Leak rows in those invalid runs still wrote a raw artifact because retention at `application.py:225` happens before the later guidance or allowance error.

Valid route results for `cont-auth`, `cont-password`, `log-cont`, and `json-cont`:

| Boundary | HTTP | Wire | Raw artifact | Status |
| --- | ---: | ---: | ---: | --- |
| route task | 1 | 1 | 1 | `ready` |
| route attachment | 1 | 1 | 0 | `ready` |

Valid discovery results for the same four texts, one round, fixture objective id kept, `output_planning_reservation` 0, `max_input_tokens` and `context_token_limit` 65536:

| Boundary | HTTP | Wire | Raw artifact | Status |
| --- | ---: | ---: | ---: | --- |
| discovery objective | 1 | 1 | 1 | `discovery_failed` |
| authorized context | 1 | 1 | 1 | `discovery_failed` |
| discovery attachment | 1 | 1 | 1 | `discovery_failed` |
| discovery description | 1 | 0 | 1 | `discovery_failed` |

The description wire count is 0 because that one-round question offered a domain node. The resource description was still stored unsanitized. A follow-up with `max_rounds` 6 made 4 HTTP calls for `cont-auth` on `discovery_description` (`probes/description-depth-receipt.json`). Wire remained 0 and the raw artifact’s `initial_state.nodes` resource description still held the original joined label and the sentinel. The public content-type control in that same follow-up also had marker 0 on the wire and marker present only in the raw artifact, so this seat does not claim the description field itself was submitted. Retention of the excluded sentinel is enough to falsify EC-ROUTE-4 on that boundary.

Consequence counted on the valid runs: 4 texts × (2 route wires + 3 discovery wires) = 20 wire disclosures, and 4 texts × (1 route raw + 4 discovery raw) = 20 raw artifacts. The depth run repeats the description retention for `cont-auth`. The password, api_key, secret, and access_token joins were confirmed at `redact`; HTTP used authorization and password.

Minimum repair: decode YAML double-quoted escapes, including the backslash-newline continuation, on the original quoted member before any original-text return. Do not rewrite the physical break into a literal `\n` in a way that hides the joined label. If the decoded label is a credential, mask every sibling or reject before reservation, dispatch, and retention. A `redact` pre-check that returns the secret unchanged must not count as validation. Keep the pure-YAML sanitizing path, the public `"pub\<newline>lic"` continuation, and Content-Type. Add these forms to the six-label × six-boundary matrix without pruning prior strings or rejection permissions. Do not execute supplied code.

### GR17-B. A same-line explicit-key value is skipped when compose fails

```text
Ordinary context.
? str('Author')+str('ization'): S
```

These pure documents also return the sentinel from `redact`:

```text
? \vstr('Author')+str('ization'): S
? \fstr('Author')+str('ization'): S
? \tstr('Author')+str('ization'): S
```

The pure space form and the pure NBSP form, without prose, reject `unsupported structured mapping key` because YAML composes them. The next-line form `? \vstr('Author')+str('ization')\n: S` rejects `unsupported concatenated literal credential`. That is the closed GR16-2 control. The same-line colon is the open form.

`context.py:384-398` captures the explicit-key value as the rest of the physical line, which includes the same-line `: value`. `ast.parse` of `str('Author')+str('ization'): S` fails. `context.py:647-657` continues on that `SyntaxError` unless the span starts with `(`. The member is never marked unsupported, and the original text returns. `INDENT` already includes VT, FF, and tab. The failure is the same-line colon span, not the absence of VT from the indent class. Ordinary space after prose shows the same fail-open.

Valid HTTP ids `space-colon-prose`, `vt-colon`, `tab-colon`, and `ff-colon` match the GR17-A table exactly: route task wire and raw, route attachment wire only, discovery objective/context/attachment wire and raw, discovery description raw with wire 0 on the one-round run and again on the depth run for `space-colon-prose`. Statuses match the table above. Together that is another 20 wire disclosures and 20 raw artifacts on the valid runs, plus the depth-run confirmation of description retention.

Minimum repair: when an explicit-key indicator is followed by `INDENT`-class whitespace, validate the key expression separately from a same-line `: value`. A recognized computed credential key must reject even when the combined span is not a Python statement. Keep the next-line VT rejection, the pure space and NBSP rejections, and ordinary Content-Type explicit keys. Do not execute supplied code. Add the four forms to the existing six-boundary matrix without pruning prior inputs.

## Round-16 repairs that hold on these exact inputs

These are this seat’s executions. They close the reported round-16 triggers. They do not close GR17-A or GR17-B.

| Input | Result |
| --- | --- |
| GR16-1 / A16-1 doubled-apostrophe single-line members, prose and pure, including the indented form and `'''Author'' + ''ization'''` | `redact` rejects `unsupported multiline quoted credential record`. HTTP `gr16-doubled` rejects on both route boundaries and all four discovery boundaries with zero requests and zero raw artifacts. |
| GR16-2 next-line VT explicit key, and the addition form | `redact` rejects `unsupported concatenated literal credential`. HTTP `vt-next-line` rejects on both route boundaries and all four discovery boundaries with zero effects. Space and NBSP next-line forms also reject at `redact`. |
| ALT-R16-1 LS/PS enclosed scalar and explicit-key forms | `redact` rejects `unsupported computed literal record`. Direct only. |
| ALT-R16-2 adjacent sequence continuations, with and without prose | `redact` rejects `unsupported concatenated literal credential`. Direct only. |
| `cont-pure` | Route and corrected discovery dispatch. Wire 0, raw 0. |
| `content-type` | Route dispatches with `application/json` on the wire. Corrected discovery objective, context, and attachment dispatch with the marker and wire 0 for the sentinel. |

Direct `redact` also rejected double-quoted `str("Author")` concatenation, hex and unicode label prose, a computed expression continued across a backslash newline, flow doubled apostrophes, plain `'Author' + 'ization'`, a comment between the key and the quote, NEL and LS explicit keys with next-line values, sequence continuations with VT or LS, and a block scalar of `str('Author')+str('ization')`. Public addition, Content-Type, and an ordinary arithmetic task stayed intact. `hex-label-pure` was sanitized. The direct sweep was 44 inputs: 34 reject, 5 clean, 5 leak. Exit 0 means the sweep finished. The five leaks are the two blocker families plus `vt-inside-quote`, which is outside the published contiguous-label rule.

## M1–M5

**M1.** Approved ROUTE discovery and task routing, offline HOST/LEARN/EXPERIMENT interfaces, CLI boundaries, schema and SDK publication, and bounded execution remain coherent on the inspected plans and the supplied exact-head receipts. The five-second product deadline, the 10000-node cap, and the injected spending gate remain. An injected judge with `policy["spending_ceiling"]` set still raises before `judge.judge` (`application.py:819`, call at `:841`). Empty `allowed_providers` stays unrestricted. No separate SDK or dependency blocker. The published sanitizer contract is false for GR17-A and GR17-B, so M1 is not acceptance of this candidate.

**M2.** Fails. GR17-A and GR17-B send an excluded sentinel and retain it. Reported replay, recovery, idempotency, deletion, and authority repairs remain supported by the supplied suite and by the spending gate re-read here. They do not offset the disclosure. Portable v1 still omits the experiment ledger and raw discovery artifacts and then blocks new experiment admissions. That remains a documented fail-closed limit. This seat did not re-execute deletion or replay.

**M3.** Root’s RETRY2 suite, HTTP receipt, CI binding, and native manifests match this HEAD on the artifacts this seat hashed and counted. JUnit SHA256 `9ed7471cba3ad56cbc8af7fb5ed749bea890fbe95c9f7124664dce870b7b7afc`, 3287535 bytes, testsuite attributes and 16912 individual testcase nodes, 0 failures, 0 errors, 0 skips, runner `575.655614193005` seconds. Loopback receipt SHA256 `a8d562b249868c1c1c1f1825dd1cdec565da2d4e19346f0abd9445486dd526c8f1`. ROUTE run `38939262942` is 16414 tests per platform, 0 failures, 0 errors, 0 skips. CONTRACT run `38939262779` is 322 per platform, 0 skips, successful named checks. This seat does not invent absent CONTRACT failure or error counters. Collection seconds are Linux 228.960, macOS 364.658, Windows 296.711. macOS `proof_cost_target_exceeded` is true. Linux and Windows are false. All three are within 600 seconds. Cold CLI is 0.351, 0.362, and 0.459 seconds. The 300-second target, the 600-second collection limit, the five-second product deadline, and the aggregate HTTP and full-suite durations are different measurements. No waiver. Companion prerequisites are explicit in the configured RETRY2 runner. This seat did not rerun the suite, the native hosts, or the companion. The default whole-diff whitespace check still flags one preexisting blank EOF line in the verbatim round-16 alternative report, SHA256 `20f14ea34c5e8035f36f50cfb9de33178fa9436123944b4ede1e395b10d0d741`. This review does not claim a clean whole-diff.

**M4.** Preserved for this seat. No secrets, `.env`, private studies, holdouts, raw streams, hidden reasoning, actual grants, deployment, promotion, or adoption. The stopped study, the disabled expired preview, and the unrelated dirty composer and companion worktrees were not modified. These software probes are not empirical acceptance.

**M5.** Each blocker names EC-ROUTE-4 and the readiness rules, the source lines, the trigger, the valid HTTP and raw consequence, and the minimum repair. Suggestions below stay suggestions. No deadline, assertion, node budget, or historical failure was relaxed.

## Prior objections

“Closed for the reported trigger” means that shape rejects or sanitizes on this head in this seat’s direct or HTTP controls, or is covered by the supplied corpus for an earlier repaired form. It does not make the finite matrix a universal privacy proof. Historical votes do not carry. Round-8 Grok’s AGREE does not carry. Round-14 and round-16 correctness AGREEs do not carry and do not cover GR17-A or GR17-B. Round-11 Astra, round-13 correctness, and round-15 Astra provider failures have `standingVerdict` null. They are not votes. Their saved probes stay partial evidence.

| Objection | This head |
| --- | --- |
| Rounds 1–5 and the cap reduction: SDK publication, provider gates, injected ceilings, model and counter preflight, portable recovery blocking, worker scrubbing, discovery retention, downstream controls, duration summation, LF checkout, schemes, folds, duplicates, normalized names, Postman records, header pairs, encoded strings | Supported by the supplied suite and the retained matrix. The handle-or-reject obligation stays open through GR17-A and GR17-B. 147 SDK files are tracked. |
| Round 6: anchors, aliases, merges, tags, comments, credential-bearing keys | Reported forms remain on the rejection path. This seat’s new leaks are not those graph forms. |
| Rounds 7–11: multiline and augmented assignments, structured keys, adjacent literals, CR/NEL/LS/PS, dash-only items, prose and Markdown records, apostrophe and `dict()` records, no-string-constant calls | Reported triggers were repaired on later heads and were not reopened by the round-16 controls this seat reran. This seat did not re-execute every historical string and did not rerun the 400000-entry CLI. The 10000-node cap remains. |
| Round 12: outer-quoted multiline YAML, mixed sequences, folded scalars, spaced and parenthesized `dict()` calls, invalid store targets | Historical DISAGREE at `b2b49960`. Later repairs cover those reported triggers. GR17-A is a different double-quoted continuation. |
| Round 13: doubled apostrophes before folding, next-line scalars, off-column quotes, comment folds, JSON-detached keys, formatted assignment targets | Historical DISAGREE at `cb2ab897`. Reported triggers are covered by later controls. The correctness task supplied no vote. |
| Round 14: unindented comments, leading VT/NBSP, unmatched quotes | Historical DISAGREE from Astra, alternative, and Grok. Correctness AGREE is historical. Reported triggers are covered by later controls. |
| Round 15: quote-normalization after decoding, false closer before newline, interior NBSP/VT, inline backticks, and the failed Astra quote-on-the-next-line diagnostic | Historical alternative and Grok DISAGREE. Astra supplied no vote. The combined round-16 repair covers those reported inputs in the supplied corpus. GR17-A and GR17-B are later compositions of the same original-member obligation. |
| Round 16 A16-1 / GR16-1, ALT-R16-1, ALT-R16-2, GR16-2 next-line VT | Closed for the exact inputs in the table above. Same-line VT, FF, tab, and prose-plus-space colons are GR17-B. The backslash-newline join is GR17-A. |
| Spending, model, counter, profile, and provider authority | The injected ceiling gate at `application.py:819` still precedes `judge.judge`. This seat did not re-execute the authority tests. The RETRY2 suite is the execution evidence. |
| Replay, recovery, idempotency, deletion | Read as the documented portable-v1 block. Not re-executed here. |
| Unratified F6/F7/D2/D4/D6 | No additional merge blocker and no empirical acceptance. |
| Historical process failures | The initial full attempt remains failed-incomplete near 21 percent, outer exit 1, empty XML, ENOSPC, pytest exit unavailable. The first retry remains interrupted near 97 percent with no JUnit and no receipt. Windows timeouts, omitted-dash disclosure, interrupted exits, the `bcf` MIME rejection, the `b2` assertion failure and its corrected rerun, development regressions, and provider failures stay historical failures. RETRY2 does not relabel them. Round-17 development failures in `evidence/MERGE/round-17/responses.md` and `development-note.txt` remain failures, including the 50-failure and 4-failure context batches, the 16-failure expanded batch, and the thirteen proposed positives that the baseline already rejected and that the new tests keep rejected. |

## Presidential requirements

`evidence/MERGE/round-5/president.md` ends `BLOCK_MERGE` at `23192913282a8e3bcc10a9a262df346791789945`.

1. One credential-label predicate after trim, case, and separators. The predicate exists. GR17-A and GR17-B never present the joined or computed label to it.
2. Decode without dropping members, and do not restore original bytes after a lossy decode. GR17-A rewrites the continuation so the joined label is not the validated text, then returns the original bytes. Open.
3. A credential label masks every sibling value. Open through both blockers.
4. Complete free-text values, with an ordinary unindented next line kept. The Content-Type and public-addition controls keep their text. The unindented-next-line observation stays a suggestion.
5. YAML, Python literals, and code assignments are handled or rejected before submission and retention. Open through both blockers.
6. Generated labels, formats, and six boundaries. The supplied matrix is 318 formats and 1908 strings and preserves the prior 282/1692, 256/1536, 233/1398, 211/1266, 191/1146, and 173/1038 strings and rejection permissions. It does not contain these inputs. Root’s 20250 boundary executions, 3375 IDs, 2709 distinct texts, 1350 reviewer IDs, 4388 requests, and 0 violations are for that corpus. They do not cover GR17-A or GR17-B.

Four fresh AGREEs and a new separate presidential ruling are unmet. This seat dissents. Source stayed unchanged through this review.

Native collection is recorded under M3. The macOS target flag stands. It is not a second blocker and it is not waived.

## Suggestions

These stay outside the blockers. This seat does not send them through HTTP and does not turn them into new goals. The owner boundary already lists them: cousin and comment associations, unquoted tuples, OpenPGP, colonless prose, unlabeled calls, XML, comparison targets, blank-line cousins, and unindented next lines. `vt-inside-quote` stays in that non-blocker class because the vertical tab splits the word, so the label is not the contiguous credential token. A repair may reject a failed parse of a recognized explicit-key member. That is the GR17-B repair. It is not a request to ban ordinary unindented prose.

## What this seat ran

- Direct `redact` sweep, 44 inputs, exit 0. Receipt `probes/direct-results.json`. Diagnostic completion, not a privacy pass.
- Mechanism traces for the pure-versus-prose continuation and the same-line colon. Receipt `probes/mechanism.json`.
- Route and first-pass discovery HTTP, 72 rows, runner about 65 seconds, exit 0. Route rows are valid. Discovery rows in that receipt are not dispatch evidence.
- Discovery follow-up that kept the fixture objective id and still made 0 HTTP requests, including the content-type control, because the fixture allowance did not match `prepare_option`. Receipt `probes/discovery-receipt.json`. Not dispatch evidence. Contract rejections of `vt-next-line` and `gr16-doubled` in that run have zero raw artifacts and remain valid pre-effect rejections.
- Corrected discovery wire, 40 rows, runner 23.72 seconds, exit 0. Receipt `probes/discovery-wire-receipt.json`. Content-type marker 1 on objective, context, and attachment shows the harness dispatched. Leak rows are privacy failures.
- Description-depth probe, 3 rows, exit 0. Receipt `probes/description-depth-receipt.json`. HTTP 4, wire 0, raw 1 on both leak descriptions. Marker 0 on the public description. Retention is the finding. Description-field submission was not shown.

No full suite, shared HOST collector, companion collector, or native host was rerun. No nested agent was started. No GitHub comment or watcher was created.

## Limits

Database retention is a byte scan of this seat’s SQLite files, not a decoded column audit. Authority, replay, idempotency, and deletion were not re-executed. The description wire result is limited by the traversal: four calls did not place the resource description on the request body. Raw retention of that description is measured. Finite tests, including root’s clean corpus, do not prove global privacy. The two invalid discovery receipts are recorded as harness failures.

DISAGREE
