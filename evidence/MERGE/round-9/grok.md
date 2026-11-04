**Do not merge Consiliency/jevdrill#1 at `b8e6ce61480e86d85645b28f711313d006582293`.** Two credential disclosures still cross the judge wire and raw retention. This is the round-9 Grok integration seat. The round-5 `BLOCK_MERGE` still governs merge until a new president rules after all four fresh seats finish. This vote is not empirical acceptance.

## Binding

Reviewed root: `/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed`, branch `codex/implementation-reviewed`. The composer checkout was not reviewed.

- HEAD `b8e6ce61480e86d85645b28f711313d006582293`
- Manifest `/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round9-20261015/candidate7/source-manifest.json`, SHA256 `7b24de1b28b31b6d3826bd9238de0890af9ad49445dc6b5a23ca12cd2cf5d3c7`, 796 tracked files
- `sha256sum --quiet -c` of `candidate7/source-manifest.sha256` from that root exited 0 before the probe and again after this report’s binding check. `git status --porcelain` was empty both times.
- Packet `candidate7/review-brief-verified.txt`, 269355 bytes, SHA256 `e90c7e7ec346f1a41a2c43241f5922d55cbabdf999106babfc3272c2c9b7163f`, read in full. The round-9 verified header is the current head. Older head lines in that packet stay attributed to their own candidates.
- Also read in full: `evidence/MERGE/round-8/{correctness,astra,alternative,grok}.md`, `evidence/MERGE/round-9/responses.md`, `evidence/MERGE/round-5/president.md`.

Seat evidence, outside the frozen tree: `/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round9-20261015/reviews/grok/seat-b8e6ce6/`

| Artifact | SHA256 |
| --- | --- |
| `evidence.json` | `54d2f560425890b2e6703876cee473b2c2f2ae9e02a41f6cecfb0ffe54cbfeee` |
| `redact.json` | `a19b80dd7abd20be6839d6d7b429c88ca708f47eaad33e56609e83acee5ddcf4` |
| `loopback.json` | `d8cd1858e3e8e9453180157a711434db8e07acbae28a54d79eed68f83afc4381` |
| `narrow.xml` | `08a7af0b69d2a7cef490c8938d31f1331ef84cb4acee5c97cb612766c7c94564` |

Sentinel: `SYNTHETIC_R9_GROK_SENTINEL`. Fake-inline DevelopmentJudge on `127.0.0.1`, fresh synthetic allowances, separate SQLite per case. No real provider, study, grant, holdout, or secret was read.

## Current blockers

`S` below is that sentinel. Each trigger was returned unchanged by `redact` and then submitted on all six boundaries: route task, route attachment, discovery objective, authorized context, description, and discovery attachment. Each boundary made one HTTP request and one reservation. Route attachments are on the wire and absent from raw-task artifacts, so each trigger leaves five raw artifacts. SQLite held no sentinel. A later `discovery_failed` did not undo the submission.

### 1. A dash-only YAML line skips the sequence guard. M2.

Published rule: a labeled header-pair sequence masks its siblings, and a mixed credential record that cannot be parsed structurally is rejected before submission and retention (`docs/route-readiness.md:62-69`). The plan requires sanitization before provider submission or persistence (`plans/phase-plan-v1-ROUTE.md:220`). The spec forbids collecting secrets (`docs/jevdrill-spec.md:394`).

The sequence scan requires whitespace on the same line as the dash:

```124:128:src/jevdrill/context.py
    for sequence in re.finditer(
        r"(?m)^[^\S\r\n]*-[^\S\r\n]+[^\r\n]*" + rf"(?:{CONTINUATION})*", text
    ):
        _check_deadline(deadline)
        credential_sequence = credential_sequence or _credential_label(sequence.group(), deadline)
```

`CONTINUATION` itself starts with a line break. A line that is only `-` never sets `credential_sequence`, so the rejection at `context.py:169-170` and `context.py:198-199` never runs.

Trigger A, space indent. `yaml.compose` returns a plain `ScalarNode`. Output is the original text:

```text
Ordinary context.
-
  Authorization
- S
```

Trigger B, tab indent. Compose raises `ScannerError`. The same flag stays false, and the original text is returned:

```text
-
	Authorization
- S
```

Consequence for these two triggers: 12 submissions, 12 reservations, 10 raw artifacts.

The same-line mixed sibling is closed. `Ordinary context.\n- Authorization\n- S` rejects with `unsupported structured credential sequence` and makes zero requests. A pure space-indented sequence (`-\n  Authorization\n- S`) composes as a `SequenceNode` and masks both items. A mixed block sequence rejects. This is the newline-only dash, which the same-line repair does not see.

Minimum repair: treat a line that is only optional indent plus `-` as a sequence item and include the following indented line in the credential scan. If compose does not yield a mapping or sequence, reject before submission and retention.

### 2. An expression-free f-string still concatenates a credential label. M2.

Published rule: ambiguous concatenated literal labels are rejected (`docs/route-readiness.md:68-69`), under the same submission invariant.

```python
{'name': 'Author' f'ization', 'value': 'S'}
```

`redact` returns that mapping unchanged. Tokenization emits `STRING` for `'Author'`, then `FSTRING_START` / `FSTRING_MIDDLE` / `FSTRING_END`. Only `tokenize.STRING` joins (`context.py:258-269`), so `concatenated` stays false and `context.py:336-337` does not reject. Plain, raw, and bytes adjacents of the same label reject with `unsupported concatenated literal credential` and make zero requests.

Consequence: 6 submissions, 6 reservations, 5 raw artifacts.

Minimum repair: treat expression-free adjacent f-string fragments as literal parts, or reject the unresolved record before any effect. Do not execute the f-string.

Together the two blockers are 18 submissions and 15 raw artifacts.

## Round-8 dissent, closed on the forms those seats ran

Those reports were at `4dd336a0282bf177f41dbc4929748289fef5d68c`. Correctness, Astra, and alternative voted DISAGREE. The round-8 Grok AGREE does not carry. Re-executed at this head:

| Prior objection | This head |
| --- | --- |
| Adjacent plain, raw, and bytes literals, including mapping keys and header-pair arrays | Reject `unsupported concatenated literal credential`. Loopback HTTP 0. |
| Implicit multiline targets: parentheses, attributes, subscripts, tuples, augmented `+=` | Reject `unsupported multiline credential assignment`. HTTP 0. |
| Bare CR between statements | Masked to `ordinary = 0[redacted]`. Wire 0 across 6 boundaries. |
| YAML block, folded, and subscript siblings whose labels assignment-rewriting used to erase | Both fields become `[redacted]`. Wire 0. Structured inspection now precedes assignment rewriting. |
| Quadratic explicit-continuation scan past the five-second CLI deadline | `"ordinary\\\n"*2000` in 0.002469s, text unchanged. `"x\\\n"*20000 + "ordinary"` in 0.008054s. The same input with a 5s deadline returned in 0.008448s. |
| `MemoryError` escaping the public JSON boundary | `tests/privacy/test_context_privacy.py` includes the boundary-error control and passed inside the 829. |

The omitted-dash fast path (`b78de2fc8`) remains a historical disclosure: 6 submissions and 5 raw artifacts, receipt `d5cd177c…`. The current marker set at `context.py:374` includes `-` and `%`. The same-line `- Authorization` input is now masked, and `fast` is false. The live leak above is the sequence regex, not that fast path.

## Presidential requirements

`evidence/MERGE/round-5/president.md` still ends `BLOCK_MERGE`. Items 1–4 and 6 hold for the forms exercised here: one substring label rule, member-preserving JSON, sibling masking inside one mapping, indented folds kept and the ordinary unindented next line kept, and a six-boundary matrix. Item 5 is still open through both blockers. YAML and Python literal records that the published contract says to mask or reject are submitted instead.

Future-approval conditions in that ruling are unchanged: the structural repair, four fresh AGREE votes, a clean full suite, nine checks on the exact head, and an unchanged head and manifest. This seat supplies one dissent. The full-suite and check receipts below are exact-head evidence. They do not replace the missing repair or the presidential ruling.

## Exact-head receipts this seat checked

From `candidate7`, hashed or reduced locally. These runs were not repeated.

- `full.xml` SHA256 `9d6ac37932a33beb9a6d6d43d4327be66a048e47e1ce4f27b324d31374b6b806`: 3863 tests, 0 failures, 0 errors, 0 skips.
- Official loopback receipt SHA256 `e3dc4e241b6666222b772e8705440efff52d254d6c5bac3958d562143e764675`, inputs SHA256 `fabb0860b34627dd1f65f2c74be529272b60e8861a9b157e731077640cfa4b5b`, receipt head is this HEAD. The candidate5 probe with colliding case IDs is not complete matrix evidence.
- `reduce_manifests` for route and contract returned zero errors. Digests: route `17a7cf0d3bdf82c36e1083b8a2790d4a73a4e40fc661dfffb30296d4724907bf`, contract `98e24144bb0f6b40214d0c9963cd9e589a365f6a77d47b4d1139deec19ea6f9a`.
- `git diff 14b7e80..HEAD -- src` is empty. The Windows temp-directory commit did not change runtime source.
- Tracked SDK files: 147. `typesafe_patch` is tracked.
- CI binding in `candidate7/ci-binding.json` was read as nine distinct checks and fourteen instances, all success, bound to this head. GitHub was not queried again.
- Recorded native durations accepted by that reduction: ROUTE 3365 tests on each platform, Windows 156.579s with cold CLI 0.623s under runner temp, Linux 102.530s, Darwin 181.821s. CONTRACT 322 on each. The five-second CLI assertion and the collector expression `timeout=max(0.001, 600 - elapsed)` are still the published limits. Verbosity and `faulthandler_timeout=30` are diagnostics. The failure-only CLI child uses a separate database.

Historical Windows failures stay failures: the early assertion failures, the 600-second collector exhaustions, the three CLI failures at `2cd84c1` before its unchanged-head retry, the continuation cases over 5 seconds at `0538011c`, and the discovery and installed-wheel timeouts at `94b54eb`. A later green run does not rewrite them. The stopped study, real grants, and the dirty composer checkout were left in place.

## What this seat ran

Redact matrix: 79 inputs. Eleven returned the sentinel. Twenty-three of those inputs went through the six-boundary loopback: 138 rows, 108 HTTP requests, 66 wire hits, 55 raw hits, 0 database hits. The 66 wire hits are exactly the eleven redact leaks. Closed controls that reject made zero requests and zero reservations.

Narrow pytest, `--basetemp` and JUnit under the seat directory, candidate `.venv`, cache writes disabled: 829 passed, 0 failures, 0 errors, 0 skips, 18.895s. The selection covered context privacy, the long-ordinary and deep-malformed CLI deadline controls, invalid input, discovery authority, the injected spending ceiling, identical-judgment replay, idempotency under changed authority, reservation crash recovery, portable recovery’s refusal to replenish experiment authority, and deletion scrubbing a completed experiment’s terminal worker content.

## Suggestions

These also returned the sentinel on all six boundaries. They sit outside the published label grammar, or the contract explicitly keeps them. They are not merge blockers.

- Two one-field YAML maps, `- name: Authorization` and `- value: S`, mask only the name. The single map `- name: Authorization` / `value: S` masks both. Sibling masking does not cross sequence items.
- Colonless `Authorization Bearer S`, space-separated `X-API-Key S`, `set_password("S")`, an unquoted `(Authorization, S)`, zero-width `pass\u200bword`, and fullwidth `ｐａｓｓｗｏｒｄ`. Parentheses and commas are outside the fast-path marker set, so the unquoted tuple never reaches the structured parser. Quoted tuples already reject.
- `api_key:\nS` becomes `[redacted]\nS`. That is the documented ordinary next line (`docs/route-readiness.md:64-65`). The indented form is masked.
- `note(password := "S")` becomes `note([redacted]`. The secret is gone. The closing parenthesis is dropped.

## Limits

The full suite, HOST companion, native Windows, Linux, and Darwin hosts, packaging, and the 2082-check official loopback were checked through their exact-head artifacts and a local reduction. They were not rerun. Authority, replay, idempotency, recovery, and deletion were checked through the named tests inside the 829, not by re-executing every recovery path. Portable v1 still omits the experiment ledger and raw discovery artifacts and then refuses new experiment admissions. That remains a documented fail-closed limitation.

No source, index, tracked evidence, or GitHub state was changed. No nested agent was started.

DISAGREE
