**DISAGREE** on `Consiliency/jevdrill#1` at `7bc8cc4c067c7cba74afbeeb59893734c4b54edd`. The round-5 credential forms, the president's listed static cases, and the spending and model gates hold. Three YAML/JSON boundary leaks still reach a judge and raw retention.

This is an independent board seat. It is not the president's ruling.

## Binding

Candidate `/home/viperjuice/workspace/worktrees/jevdrill-implementation-reviewed`. HEAD `7bc8cc4c067c7cba74afbeeb59893734c4b54edd`. Delta base `23192913282a8e3bcc10a9a262df346791789945`. PR base `f67ad654ff224d6b343ab366260d9184150d822f`. Manifest `/tmp/jevdrill-merge-review-20261012/round-6/source-manifest.json`, 779 files, SHA-256 `da573088891c85c51c96e654e981bafdfbef09623d83de1917855137fa4c8889`. `sha256sum --quiet -c` passed before the probes and again after them. HEAD and tracked status stayed unchanged.

## Round-5 and president requirements

Closed, by running `redact` on the reported inputs:

- Trailing whitespace before folded Authorization, API-key, and password values, including the ordinary next line.
- Multiword `password: correct horse <sentinel>`.
- Duplicate JSON members. Both copies stay in the YAML node list and the sentinel is removed. The old "decode, then put the original bytes back" path is gone for this case.
- `name` / `Name` / `na_me`, and a header name with leading or trailing whitespace.
- Standalone and nested JSON strings.
- Postman `key` records, in-array header pairs, `client_secret`, `X-Goog-Api-Key`, YAML `name`/`value`, Python literals, and subscript assignments.
- A 1,500-deep bracket nest raises `ContractError` (`context nesting exceeds sanitization limit`) from `context.py:123-124`. `yaml.compose` of a `!!python/object/apply` tag returns a node and does not call the constructor.
- A second YAML document makes `yaml.compose` raise `ComposerError`. The free-text scanner then redacts `api_key:` in the following document.

The same-map alias in `tests/privacy/test_context_privacy.py` also stays clean, because the anchor is the mapping and the first visit rewrites that mapping's values.

Authority and cost gates are unchanged in this delta and still fail closed. `Application.route` checks an injected ceiling at `application.py:802-811` before `judge.judge`. `Application.discover` checks it at `application.py:283-296`. Thirteen current tests passed in 8.48s: built-in `$0` and `$1`, plus injected allow, unsupported model, mismatched model, bad counter, and ceilings of zero, `$0.001`, funded `$1`, missing rate, positive output rate, stale rate, and EUR. Denied cases record no judge request. Funded injected pricing remains unsupported. Portable v1 still omits the experiment ledger and raw discovery artifacts.

The recorded full suite at `/tmp/jevdrill-merge-r6-full.xml` matches SHA-256 `b9d88f0781488bfa9e2bd77c22096c12de49903ba589ed35dbe66b1f5a8dcce8`: 1638 tests, 0 errors, 0 failures, 0 skips, 709.819s. I parsed that XML and did not re-run the suite. GitHub Actions on this exact HEAD succeeded for all nine jobs: [CONTRACT 38340191525](https://github.com/Consiliency/jevdrill/actions/runs/38340191525), [ROUTE 38340191490](https://github.com/Consiliency/jevdrill/actions/runs/38340191490), and [EXPERIMENT 38340191508](https://github.com/Consiliency/jevdrill/actions/runs/38340191508). This seat queried those runs. The round-5 seven HOST timeout errors are historical.

`hard_constraints.spending_ceiling` remains the execution-plan cap. Conformance transport deadlines are outside this delta.

## Open blockers

All three violate sanitization before submission and persistence (`plans/phase-plan-v1-ROUTE.md:220-221`, `docs/route-readiness.md:56-57` and the new fail-before-submission rule at `docs/route-readiness.md:65-66`) and the prohibition on collecting secrets (`docs/jevdrill-spec.md:394`). Sentinel `SYNTHETIC_R6_GROK_SENTINEL`. Receipt `/tmp/jevdrill-r6-grok-receipt.json`, SHA-256 `25c5d116e463a9cb598bc214179e6247fba06bc0c462435cbb3ee139fc65374d`.

**P1. A YAML scalar anchor escapes the masked container.**

`_redact_node` replaces a sensitive value with a new `[redacted]` node at `src/jevdrill/context.py:51-52` and replaces a sensitive sequence the same way at `context.py:57-60`. It does not write `[redacted]` into the existing scalar. Another alias still points at the original secret, and `yaml.serialize` emits it.

```yaml
token: &s SYNTHETIC_R6_GROK_SENTINEL
headers:
  - X-API-Key
  - *s
```

`redact` returns the sentinel on `token` while both header entries are `[redacted]`. The same split happens for `wrapper.api_key: &s <sentinel>` / `also: *s`, and for `shared: &s <sentinel>` / `use.api_key: *s`.

Consequence, actual DevelopmentJudge against loopback, one HTTP request, status `ready`: the route task put the sentinel on the wire and in the raw artifact for the outer alias and the header-pair alias. The route attachment put it on the wire. Raw task retention stores `task_representation` only (`application.py:951-955`), so the attachment disclosure is the judge body (`application.py:812-830`). Replacing the discovery objective, authorized context, or description with the same document submitted and retained the sentinel through the discovery observer. Appending the document to ordinary prose does not: the free-text scanner then consumes the `api_key:` line. The whole supplied value is the leaking shape.

Minimal repair: mask the existing scalar in place when its container is sensitive, including a scalar anchored outside that container. Fail closed if a labeled alias still resolves to the original secret.

**P1. An unchanged YAML document returns comment text the parser dropped.**

`_structured` returns the original string whenever `_redact_node` reports no node change (`context.py:79`). Comments are not nodes. These two whole values come back with the sentinel:

```yaml
note: ordinary  # api_key: SYNTHETIC_R6_GROK_SENTINEL
```

```text
{"note":"ordinary"} # api_key: SYNTHETIC_R6_GROK_SENTINEL
```

A comment beside an already sensitive key is dropped, because that document is serialized from nodes. A comment on an ordinary mapping is preserved and submitted.

Consequence: the same DevelopmentJudge route task returned `ready`, made one HTTP request, and kept the sentinel on the wire and in the raw artifact. The route attachment put it on the wire. Discovery objective, context, description, and attachment did the same when the field value was the comment document. A secret inside prose-plus-comment is caught by the free-text scanner.

Minimal repair: if the composer did not represent a region and `CREDENTIAL` still matches the original text, redact that match or raise `ContractError` before submission and retention. Keep returning the original bytes for ordinary JSON that does not match.

**P1. A credential-labeled JSON key keeps the secret.**

`{"Authorization Bearer SYNTHETIC_R6_GROK_SENTINEL": "x"}` is a sensitive mapping, so the value becomes `[redacted]`. The key is kept. `redact` on that key (`context.py:64-67`) does not match: the assignment pattern needs `:` or `=`, and the Bearer alternative does not match after another word (`context.py:21-27`). `api_key=<sentinel>` as a key, and `Authorization: Bearer <sentinel>` as a key, are removed.

Consequence: the route task and route attachment above returned `ready`, made one HTTP request, and the task form retained the sentinel. The key still contains an Authorization secret after structured sanitization.

Minimal repair: a scalar that matches the credential-label predicate and carries anything beyond the bare label is replaced with `[redacted]` before serialization.

## Verification and limits

`redact` checks covered the historical matrix, the president's static cases, ordinary arithmetic text, unindented following lines, alias escape, comments, and key shape. Route HTTP used `DevelopmentJudge` on `127.0.0.1` with a synthetic allowance. Discovery replacement used the in-process discovery observer, which receives the same post-`redact` string `_sanitize` stores (`application.py:68-70` and `application.py:104`). No live provider, study, grant, or holdout.

Two thousand, four thousand, and eight thousand unmatched `{` characters each took about 0.7s inside `redact`. That does not show the old copy-the-remainder curve. I did not push that input through the five-second CLI deadline, so it stays a residual cost, not a blocker. A zero-width character inside `authorization` still bypasses the stated label predicate. That predicate is trim, case, and the declared separators. I am not adding a new unicode-evasion blocker on top of the three leaks above.

The outside-git `binding.json` still says the full suite and CI are pending. `verification.json`, the XML, and the GitHub runs above are the current receipts.

No nested delegation, source or evidence edits, secret or raw-stream reads, GitHub comments, deployment, or adoption. Historical dissents stay historical.

DISAGREE
