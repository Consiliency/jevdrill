# Round-11 Grok seat: Consiliency/jevdrill#1

**Do not merge at `346e800909dcd59317c41b7cfdf25040ca07919c`.** One M2 disclosure remains. Computed credential labels that are YAML scalars, or `dict()` keyword records, still reach the judge and raw retention. The same expressions inside braces, assignments, and subscript scalars reject. This is the Grok integration seat. It is not the separate president. The round-5 `BLOCK_MERGE` stays in force until four fresh AGREEs and a new presidential ruling.

## Binding

Reviewed root: `/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed`, branch `codex/implementation-reviewed`. The composer checkout was not reviewed.

- HEAD `346e800909dcd59317c41b7cfdf25040ca07919c`
- Manifest `/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round11-20261016/candidate2/source-manifest.json`, SHA256 `878af684f2df5458c46b87ee986f73219464d78bfb3e0fe13a9cf04772937f34`, 806 tracked files
- From that root, `sha256sum --quiet -c` of `candidate2/source-manifest.sha256` exited 0 before the probes and again immediately before this report. `git status --porcelain` was empty both times. `context.py` on disk matches its manifest entry `4331ebd23d5fed1575778eb3dc0b74cd58aa4680cd9019a7f8a81d341e79a0dd`.
- Packet `candidate2/review-brief-verified.txt`, 423484 bytes, SHA256 `3e4060c34ba977bf1dbbf54d719ccaec8b2c9e3dd36e55e2e2f5d8326de5cee2`, read in untruncated chunks. The first current round-11 VERIFIED header governs. Older heads inside the packet stay bound to their own candidates.
- Also read in full: `evidence/MERGE/round-10/{correctness,astra,alternative,grok}.md`, `evidence/MERGE/round-11/responses.md`, `evidence/MERGE/round-5/president.md`, and the correctness reviewer's saved on-disk report carried at the end of the packet.
- PR https://github.com/Consiliency/jevdrill/pull/1 is linked to this thread and is not watched.

Seat directory, outside the frozen tree: `/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round11-20261016/reviews/grok/seat-346e800-r11b/`

| Artifact | SHA256 |
| --- | --- |
| `probe_redact.py` | `4e2ace09d8c4d91c19e5a39a20543db71db697527c1be1b7d739643e33febaae` |
| `redact.json` | `bce1015e37a396c8318edf1bdeb6adf9f3c6ea52f1bdf9645d792389ee16f765` |
| `probe_http.py` | `dc8287e643e14d052e1152ca05e017d22920275c850f229bd989823c1963235e` |
| `loopback.json` | `94024032b837a34f6ea8bf176de058136d4273d496de78bac7d0b8736754e698` |
| `reduction.json` | `68e7f859658f7004b745b41985806aba340b931de28e65b96a20d1706c6c758f` |
| `cli-deadline.xml` | `a96ff591e549e73f1fa5364d6d0dd50ffa8c475e9671855a5b2bc15abf96e159` |

Sentinel: `SYNTHETIC_R11_GROK_SENTINEL`. Fake-inline `DevelopmentJudge` on `127.0.0.1`, credential lambda `synthetic-local-only`, authorize lambda true, `retain_raw_tasks` true, a fresh SQLite file per case. No real provider, study, grant, holdout, or secret was read.

## Current blocker

**P1. Unresolved computed labels that are YAML scalars, or `dict()` name/value records, are accepted and the sibling secret is submitted. M2.**

Invariant:

- Sanitize context before provider submission or persistence (`plans/phase-plan-v1-ROUTE.md:220`).
- EC-ROUTE-4 is falsified by a retained or sent excluded sentinel (`plans/phase-plan-v1-ROUTE.md:410`).
- Complete bracketed records are inspected independently of prose or Markdown. Unresolved computed literal records reject even when they contain no string constants. Structured parsing validates those records (`docs/route-readiness.md:78-82`).
- Presidential requirements 3 and 5: sibling values are masked whatever the member names or order, and YAML, Python literals, and code assignments are handled or the request fails closed before submission and retention (`evidence/MERGE/round-5/president.md`).

Source, `src/jevdrill/context.py`:

- The walk marks a node as a literal record only for `Dict`, `List`, `Tuple`, `Set`, `Subscript`, and comprehensions (`context.py:401-414`).
- An expression whose static string cannot be resolved sets `unresolved` only when `literal_record` is already true (`context.py:429-437`).
- The raise `unsupported computed literal record` runs only if no sensitive assignment already rewrote the fragment (`context.py:506-508`).
- `_structured` calls that walk and, when it does not raise, returns the original text or a node serialization (`context.py:287-291`).
- A scalar raises `unsupported embedded credential assignment` only when assignment rewriting would change the scalar (`context.py:172-177`). An unchanged computed scalar does not raise, so the parent mapping is accepted.

A YAML block, explicit key, or plain key whose value is a `Call` or `BinOp` is not inside a Python container, so `literal_record` stays false. `_credential_label` never sees the composed word. `dict(name=<computed>, value=<sentinel>)` is the same gate: the call arguments are not a `Dict`/`List`/`Tuple`/`Set`. The braced form of the same expression sets `literal_record` and rejects. A static attribute such as `headers.authorization` still masks siblings, because the label substring is already present.

Triggers returned unchanged by `redact`. `S` is `SYNTHETIC_R11_GROK_SENTINEL`.

```yaml
name: str('Author')+str('ization')
value: S
```

```yaml
name: str('Author') + str('ization')
value: S
```

```yaml
? str('Author')+str('ization')
: S
```

```yaml
str('Author')+str('ization'): S
```

```yaml
name: chr(97)+chr(112)+chr(105)+chr(95)+chr(107)+chr(101)+chr(121)
value: S
```

```yaml
name: prefix + suffix
value: S
```

```yaml
name: header_name()
value: S
```

```yaml
name: '{}{}'.format('Author', 'ization')
value: S
```

The same block call also leaks after ordinary prose, and as a sequence item `- name: str('Author')+str('ization')` / `value: S`.

```python
dict(name=str('Author')+str('ization'), value='S')
dict(name=chr(97)+chr(112)+chr(105)+chr(95)+chr(107)+chr(101)+chr(121), value='S')
dict(name=prefix+suffix, value='S')
```

The braced equivalents, assignment targets, subscript scalars, slices, attributes, conditionals, Boolean expressions, and computed lookups reject with `unsupported computed literal record` or `unsupported concatenated literal credential`. Those closed controls made zero HTTP requests.

**Actual consequence.** Eleven of these inputs were sent through all six boundaries: route task, route attachment, work objective, authorized context, description, and attachment refs. Receipt `loopback.json`.

- 66 local HTTP requests contained the sentinel.
- 66 judgment reservations were written.
- 55 raw artifacts retained the sentinel. Route attachment is on the wire and absent from raw-task artifacts, so each of the 11 inputs leaves five raw artifacts.
- SQLite scans found no sentinel.
- Route returned `ready`. Discovery on the objective returned `discovery_failed` after the request. The other discovery fields returned `selected_guidance`. A later failure does not undo transmission.

The two extra redact leaks in the same family (`str('Author') + str('ization')` with spaces, and `dict(name=prefix+suffix, ...)`) were confirmed at `redact` and were not repeated on HTTP. The eleven HTTP inputs already establish the disclosure.

The braced reject control `{name: chr(...)+..., value: S}` returned `rejected:unsupported computed literal record` on all six boundaries: 0 HTTP, 0 artifacts, 0 reservations. Ordinary prose and a Content-Type control each made 6 HTTP requests with the sentinel absent from the wire, the raw artifact, and the database.

**Minimum repair.** Reject an unresolved computed expression that `_literal_string` cannot resolve when it is a scalar member of a structured mapping or sequence, or when it forms a name/value record, including `dict(name=..., value=...)`. Do this before submission and retention. Do not execute the supplied expression. Do not reject every call or binary operation. These must stay unchanged:

- `headers['Content-Type'] = 'application/json'`
- `headers['Content-Type'] = mime()` followed by an ordinary next line
- `{'name': 'Content' + '-Type', 'value': 'application/json'}`
- `{count: -2, label: notes}` and `{"count": -2, "label": "notes"}`
- dash-only YAML sequences and ordinary following text

## Repair claims that hold on this head

Confirmed by this seat's `redact` matrix (83 inputs: 47 reject, 18 clean, 18 leak) and by the HTTP controls above.

1. Braced records, including nested valid records inside invalid wrappers, and expression-free f-string concatenation, reject. Parsed parents cover those children. The fragment-work cap is present at `context.py:388-390`.
2. The round-10 no-string-constant forms reject when they are already inside a Python container or an assignment: `chr` chains, `header_name()`, `prefix + suffix`, slices, attributes, conditionals, Boolean expressions, and computed lookups.
3. Static supported assignment targets still mask the value and keep the following ordinary line. `headers.authorization` as a YAML scalar masks the sibling. Non-credential computed targets used as Content-Type stay usable.
4. A 400,000-entry sequence, 800,001 characters, rejects in `redact` in 0.059 seconds with `context structure exceeds sanitization limit`. The node cap is 10,000 scalars/containers before composition (`context.py:214-216`). The three CLI deadline tests (400,000-entry request, 5,000 incomplete private-key lines, 20,000 braces) passed in 1.42 seconds under the unchanged five-second assertion. Ordinary YAML flow and signed JSON numbers stay. A presentation operator outside a record does not by itself imply an unresolved record.
5. `tests/conftest.py` has 173 formats and the same six labels. Prior 95 formats, 570 format/label strings, and prior rejection permissions are recorded unchanged in the candidate's matrix-preservation evidence. This seat did not rebuild that matrix.
6. Dash-only sequences, standalone Basic/Bearer folds, a complete private-key block, and an ordinary following line stayed clean at `redact`. The incomplete private-key CLI control passed inside the five-second bound.

## Prior objections

Historical votes do not carry. Round 10 was four DISAGREEs on `392f2234f397aaee0725c6b37c9ef42c15587bf7`. The round-8 Grok AGREE on `4dd336a0` does not carry. The first round-11 candidate `7f9030631` was interrupted with exit 143 and is not acceptance. Development's separate 6,936-pass run is not this head's acceptance.

| Objection | This head |
| --- | --- |
| Round-10 inline, Markdown, and assignment concatenation (`Author`+`ization`, f-string fragments) | Reject `unsupported concatenated literal credential`. |
| Round-10 / Astra / Grok braced records with no string constants: `chr`, `header_name()`, `prefix+suffix`, slice, attribute, conditional, Boolean, lookup | Reject `unsupported computed literal record` for those braced and assignment triggers. The YAML-scalar and `dict()` forms of the same expressions are the blocker above. |
| Alternative round-10 YAML call mappings and keys that were braced | Reject. Block, explicit, and plain YAML scalars of the same calls are the incomplete repair. |
| Alternative round-10 400,000-entry deadline | Closed. Direct `redact` 0.059s reject. CLI test passed under 5 seconds. |
| Round-9 bare CR, NEL, and Unicode line boundaries; dash-only sequence items | Re-executed dash control is clean. The published line-boundary contract is unchanged. |
| Round-9 standalone Basic/Bearer indented folds | Re-executed control keeps ordinary text and removes the credential fold. |
| Round-9 constant-expression assignment targets (`"Author" + "ization"`) | Reject when the target is an assignment. Content-Type addition stays. |
| Round-9 expression-free f-string labels inside braces | Reject. |
| Round-9 quadratic incomplete private-key scan | CLI control of 5,000 openers passed inside the five-second bound. Complete PEM stays redacted. |
| Round-8 adjacent literals, implicit multiline targets, bare-CR assignments, YAML blocks erased by assignment rewriting, continuation scan, parser `MemoryError` | Reported forms reject or mask. Assignment-following ordinary text stays. |
| Round-7 augmented assignment, NBSP/VT/FF block labels, raw/f/bytes multiline assignments, structured mapping keys, escaped labels, leading-whitespace scan | Reported forms reject or mask on the re-executed subset. The full suite covers the generated matrix. |
| Round-6 aliases, merges, tags, comments, credential-bearing keys, encoded labels, arbitrary-field mixed records | Anchors still reject `unsupported YAML graph or tag`. Comment-dropped `chr` records reject. Reported graph support stays removed. |
| Round-5 trailing whitespace, multiword passwords, duplicate members, `name`/`Name`/`na_me`, trimmed labels, nested JSON, Postman keys, header pairs | Static JSON, static YAML, Postman, and header-pair controls are clean at `redact`. |
| Round-4 folded Authorization, including ordinary unindented next line | Assignment-following control keeps the ordinary line and redacts the credential. |
| Round-2/3 injected spending, model/counter, provider allowlist, recovery admission block, worker scrub, imported tombstones, discovery retention, SDK tracking, duration sum, LF checkout | Source gates remain. This seat did not re-execute those tests. The exact-head full suite is the evidence. Portable v1 still omits the experiment ledger and raw discovery artifacts and then refuses new experiment admissions. |
| Omitted-dash disclosure on `b78de2fc`, colliding case IDs, historical Windows failures and timeouts, parser deadline misses | Those outcomes stay failed or incomplete. A later green run does not rewrite them. |
| Unratified F6/F7/D2/D4/D6 | No additional merge blocker and no empirical acceptance. |

## Presidential requirements

From `evidence/MERGE/round-5/president.md`, still `BLOCK_MERGE` at `23192913282a8e3bcc10a9a262df346791789945`.

1. One credential-label test everywhere. The predicate exists. Computed YAML scalars and `dict()` records never reach it. Open through the blocker.
2. Decode without losing members. No new duplicate-member leak in this seat's controls. Holding for the reported forms.
3. Sibling masking independent of names and order. Unmet for the YAML and `dict()` computed records above.
4. Complete free-text values and folds, with the ordinary unindented next line kept. Holding on the re-executed controls.
5. YAML, Python literals, and code assignments handled or failed closed. Unmet.
6. Generated labels × formats × six boundaries. 173 formats and six labels are present. They do not include these block and `dict()` forms. The supplied HTTP matrix has 456 reviewer input IDs and does not contain these surfaces.
7. Clean exact-head full suite and nine checks. Holding on the receipts below. This seat hashed and reduced them. It did not rerun the suite or the native hosts.
8. Four fresh AGREEs and a new separate presidential ruling. Unmet. This seat dissents. The prior `BLOCK_MERGE` remains.
9. Unchanged source through review. Satisfied for this seat. It is still required at any later merge.

Future approval in that ruling still requires the structural repair, four fresh AGREEs, a clean full suite, nine checks on the exact head, and an unchanged head and manifest. The owner authorized continuation past the former cap and required the separate president. No invariant was waived.

## M1–M5

- M1. Plans, CLI, schema, and SDK publication remain coherent on the evidence inspected. The five-second CLI bound is unchanged and the 400,000-entry request rejects inside it. No new M1 blocker.
- M2. Open. The blocker above sends an excluded sentinel and retains it.
- M3. Exact-head packaging evidence holds as hashed below. 147 SDK files are tracked, including `typesafe_patch`. This seat did not rebuild a wheel or rerun the companion. An omitted companion environment would be an invocation failure, not a product defect. No new M3 blocker.
- M4. No secrets, private studies, holdouts, raw streams, hidden reasoning, grants, deployment, or adoption. The stopped study, the expired real preview, and the composer and companion worktrees were not touched. This software check is not empirical acceptance.
- M5. The blocker cites the invariant, the source lines, the trigger, the HTTP consequence, and the minimum repair. The suggestions below stay suggestions.

## Exact-head receipts this seat checked

These runs were not repeated. Hashes and reductions were recomputed locally.

- `full.xml` SHA256 `f087c2a226e6191e7f3588fb92f1d6cd9d55235254d8a68ed73c77c3b5010bfe`. Parsed counts: 9865 tests, 0 failures, 0 errors, 0 skips. `full-receipt.json` binds this HEAD, exit 0, duration 712.430 seconds, and the same manifest digest. Before and after that run the worktree was clean.
- Loopback receipt SHA256 `28ac44eaaa9cc8f793b87cc837a697e717df08522c55f2a50e249653e8ee5fa4`. Inputs `eb658a40ffdb59960020aafbbbb518c62f8bcc0fd7d4f4ded01067dba6b2bd63`. Reviewer inputs `1317d7f4b98ef86baa88a8382b47730cec64bc6749de25d22b166d00fe5a8484`. Parsed: 9294 rows, HTTP sum 2424, rejections 6870, wire sentinel 0, raw sentinel 0, on its own inputs. Those inputs omit the surfaces in the blocker.
- `ci-binding.json` binds this HEAD. 14 instances, 9 unique names, all success: Contract on macOS, Ubuntu, and Windows plus reduce; EXPERIMENT offline; ROUTE native Darwin, Linux, and Windows plus reduce.
- This seat ran `reduce_manifests` read-only. Route digest `dee8386438732212b99c212b4e2990714cb0632549baa8e9d2afa22973609687`, errors empty, 9367 tests and 0 failures/errors/skips on Darwin, Linux, and Windows. Contract digest `d9df6cc0a328e87d876b64bac0f4cd5fd177f53c9a41d829315abb484c97062f`, errors empty, 322 tests and 0 skips on each platform. All six native manifest file hashes match `native-reduction.json`. ROUTE run `38865922750` and CONTRACT run `38865922669` record `success` on this HEAD. Cold CLI `response_status` is `ready` on each route platform. `proof_cost_target_exceeded` is false.
- GitHub was not queried again and was not commented on.

## What this seat ran

- `redact` matrix: 83 inputs. 18 returned the sentinel. 14 of those are the blocker family. 4 are the suggestions below. 47 rejected. 18 were clean, including Content-Type assignment, `mime()` on the right-hand side, `Content + '-Type'`, signed `{count: -2, label: notes}`, dash-only YAML, Basic fold, PEM, and ordinary following text.
- HTTP: 14 cases × 6 fields = 84 rows, 7.92 seconds, process exit 0. The 11 leak inputs produced 66 wire disclosures and 55 raw disclosures. The reject control produced none.
- CLI deadline pytest, candidate `.venv`, private `--basetemp`, cache provider disabled: 3 passed, 0 failures, 1.42 seconds.
- Direct 400,000-entry `redact`: 0.059 seconds, reject.
- Native reducers, as above. Collectors were not invoked.

## Suggestions

These still return the sentinel from `redact`. They sit outside the published label, separator, and assignment grammar. They are not promoted.

- `(password, 'S')` unquoted. Quoted tuples already reject.
- OpenPGP armor. The delimiter is `PRIVATE KEY-----`; `BLOCK` sits between `KEY` and the dashes, so the private-key scanner does not take it.
- `The password is S today`, with no colon or assignment.
- `set_password('S')`, an unlabeled call.
- `<api_key>S</api_key>`, colonless markup.

The earlier placement-as-matrix-dimension test note remains a test improvement.

## Limits

The 9,865-test suite, the HOST companion, native macOS, Linux, and Windows hosts, wheel build, and SDK generation were checked through exact-head artifacts and a local reduction. They were not rerun. Authority, replay, idempotency, recovery, and deletion were read in source and are covered by that suite receipt. This seat did not re-execute those tests. Two same-family redact leaks were not repeated on HTTP. The official loopback's zero-disclosure result is accurate for its own 456 reviewer inputs and does not cover this blocker.

No source, index, tracked evidence, or GitHub state was changed. No nested agent was started. No deadline, assertion, or failure was altered.

DISAGREE
