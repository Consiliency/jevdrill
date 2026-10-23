Independent alternative-seat full-PR review — Consiliency/jevdrill#1

Do not merge this candidate. One independently reproduced P1 privacy blocker remains: recognized continuation whitespace can defeat the new original-scalar validation, allowing computed credential labels and their values through all six supplied-context boundaries. This is a fresh board-seat assessment, not a presidential ruling or merge authorization.

**Binding and complete reading**

Every repository command used `/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed` explicitly. Before and after review:

- HEAD: `b5b4796324324d6e7518be3f0e9faf5bc9d50ae3`.
- Worktree status, including untracked files: empty. Cached/index diff: empty.
- All 824 tracked source/evidence hashes passed the prescribed `sha256sum --quiet -c` command, exit 0, with no mismatch output.
- Source-manifest SHA256: `57d11a17c8693a65f23ddd6c1631c2b27349a7443f519892a45b355671378986`.
- Packet: exactly 757469 bytes; SHA256 `42751ed98cd8fb8b4a7b36898875dc0d5e3581acabe19f43ea13944563a38f53`.

Evidence is saved under `/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round14-20261016/reviews/alternative/seat-20261016T113735483918Z/`. `before.json` and `after.json` record the freeze checks.

I read the entire packet through untruncated tool displays, including nested historical narratives. The 32 final usable half-open byte intervals were:

```text
0:24000          24000:48000      48000:72000      72000:96000
96000:120000     120000:144000    144000:168000    168000:192000
192000:216000    216000:240000    240000:264000    264000:288000
288000:312000    312000:336000    336000:360000    360000:384000
384000:408000    408000:432000    432000:456000    456000:480000
480000:504000    504000:528000    528000:552000    552000:576000
576000:600000    600000:624000    624000:648000    648000:672000
672000:696000    696000:720000    720000:744000    744000:757469
```

Earlier oversized displays of 24000:72000, 144000:192000 and 192000:240000 were truncated, marked unusable, and fully reread in the intervals above. `reading-ledger.jsonl` retains those corrections; `packet-complete-ledger.json` records every usable chunk and hash. Its SHA256 is `3523e7f2fb790b5b7635494f78f94317915fba3523d7f5f40c1c55ebafd598a7`. Final audit verified contiguous coverage and every chunk hash.

I additionally read all 38 earlier referenced report/response/disposition files collected in `earlier-reports.txt`, including the scoped EXPERIMENT rounds 1–3, MERGE rounds 1–5 and cap reduction. Its 240316 bytes were read in these contiguous intervals:

```text
0:24000 24000:48000 48000:72000 72000:96000 96000:120000
120000:144000 144000:168000 168000:192000 192000:216000
216000:240000 240000:240316
```

`earlier-index.json` identifies each original file and SHA256; `earlier-reading-ledger.jsonl` binds the displayed chunks. The complete round-5 president was included, not merely its summary. I also separately read complete round-14 `responses.md`, the scoped final binding/closeout, all requested current proof records, the complete root HTTP probe, and the relevant plans/interfaces/source. Large machine receipts were parsed in full and checked row by row, rather than represented as manually displayed millions of bytes. The first round-14 header and current `verification.json` govern; nested pending statuses and votes retain their historical scope.

**Current blocker ALT-R14-1 — P1, M2 / EC-ROUTE-4: fallback validation silently accepts credential records when recognized indentation is invalid Python syntax**

Existing requirements are `plans/phase-plan-v1-ROUTE.md:220` (sanitize before submission/persistence), its EC-ROUTE-4 criterion at line 410, `docs/jevdrill-spec.md:394`, and `docs/route-readiness.md:60–95`. The latter expressly covers mixed records, constant string addition, NEL/Unicode line separators, original first-line/explicit-key/comment associations, and rejection of unsupported representations. These are existing requirements, not newly proposed Unicode vocabulary or unlabeled-secret recognition.

Concrete synthetic inputs include the following Python string notation; the escapes represent actual characters in the supplied string, and `S` is the synthetic sentinel:

```python
"Ordinary context.\n?\n\v'Author' + 'ization'\n: S"
"Ordinary context.\nname:\n\v'Author' # ordinary\n\v+ 'ization'\nvalue: S"
"Ordinary context.\x85name:\x85\u00a0'Author' + 'ization'\x85value: S"
"Ordinary context.\u2028?\u2028\u00a0'Author' + 'ization'\u2028: S"
```

Each contains a statically identifiable Authorization label. All four survive directly, as a JSON-encoded string, and nested under a JSON `log` member: twelve exact failing inputs.

The mechanism is visible at `src/jevdrill/context.py:289–298`: fallback recognizes the original scalar span using the shared `INDENT`/`LINE_BREAK` rules, normalizes line breaks, then passes a parenthesized validation view to `_redact_assignments`. It leaves vertical-tab/NBSP indentation intact. Python AST parsing rejects that indentation; both parsing attempts at lines 514–526 catch `SyntaxError` and continue without marking the record unsupported. Later plain-text extraction at lines 790–810 does not recover the complete association. Its colon-value pattern still requires nonempty first-line text and does not cover the bare explicit-key form. Original secret-bearing text consequently survives. An independent diagnostic showed that changing only indentation in the validation view to ASCII spaces makes all four examples reject as `unsupported concatenated literal credential`; source remained untouched.

Application sends the surviving text through task judgment at `application.py:841` and discovery observation at `application.py:336`. Opt-in raw retention uses the same values at `application.py:225` and `application.py:963`.

I reproduced the consequence with the actual DevelopmentJudge and a fresh local HTTP server, independent synthetic allowances, separate databases, and no supplied-code execution:

| Inputs | Boundary executions | Result |
|---|---:|---|
| Four failing records, each plain / JSON string / JSON object | 72 | 72 HTTP-body disclosures; 60 raw-artifact disclosures |
| Six corresponding repaired controls | 36 | All rejected before HTTP, artifact creation and judgment reservation |
| Six ordinary positive controls | 36 | All dispatched with explicit expected markers preserved |

Total: 144 executions, 108 HTTP requests. No database-file sentinel disclosure was observed. Route attachments are submitted but are not included in raw-task artifacts, explaining 60 rather than 72 raw disclosures. Routing returned `ready`; discovery returned `selected_guidance` or `discovery_failed`. A later failure does not undo transmission or retention.

The HTTP probe intentionally ended **exit 1**, failing its unchanged `assert not leaks`; it is a reproduced failure, not a passing check. Artifacts:

- `http/probe.py`, SHA256 `d1c1247b1abef174cf2dc55062847aed6e956595b7ba76993de4ec60efd6f630`.
- `http/inputs.json`, SHA256 `8f96cab2ecaa753439c852c50d250af0728455842cdf4e63036d4a1d90db525a`.
- `http/receipt.json`, SHA256 `08637af438fada43fbf291cdeb97a03139eb29fd47392826b99b1cef57221a18`.
- `http/summary.json`, `http/probe.log`, and `supplement.json` contain counts and diagnosis.

**Minimum repair:** make original scalar validation consistent with its recognized line/indentation grammar. Preserve physical comment boundaries and member associations while normalizing supported indentation in the validation view, or fail closed when that record cannot be analyzed. A failed AST parse must not establish that this recognized credential record is safe. Retain ordinary Content-Type/MIME/next-line controls. Add the four exact forms and their encoded forms through all six boundaries, then repeat frozen-head proof and the fresh board/president process. This review makes no source changes and requires no new provider, study or feature.

**Independent checks and supplied proof**

I executed 3,297 distinct targeted repository tests: 3,282 passed in 36.82 seconds and 15 passed in 1.99 seconds, zero failures/errors/skips. They cover the context matrix, DevelopmentJudge authority/profile/spending/replay, experiment recovery/admission/cancellation, retention, storage recovery, phase reducers, direct/imported terminal worker byte scrubbing, discovery expiry/deletion, built-in pricing/provider controls, selected projection/Boolean suitability, and legacy v1 replay. JUnit hashes:

- `targeted.xml`: `65dff68dddaaa557e736cad1d34de0b44b03f6a5c6760f82a77381d3b28dd9e6`.
- `lifecycle.xml`: `02e6fea8a3e631244b099ea2d7e85de039588ea9f5aee37f00cc995367931fe4`.

My 244-input structural diagnostic found 66 sentinel-surviving cases, 176 rejections and two ordinary preserved controls. It is diagnostic coverage, not 244 passing assertions. The narrower HTTP reproduction above establishes the blocker. Its original long display was truncated; the complete JSON is retained and the full list/count was subsequently inspected.

I independently replayed all 2,445 supplied input IDs through `redact`: no supplied sentinel survived, all 97 designated positive markers remained, and 1,895 inputs rejected directly. This validates those exact cases; it does not cover the new inputs. `supplied-direct-replay.json` records every result.

I independently audited, without rerunning the full suite or native collectors:

- All 12,781 supplied JUnit cases, including uniqueness and package tests: zero failures/errors/skips, matching SHA256 `40a7e52542ba02ef32cc3d350909dc6efa455b8095ec0ed2f86ea9b4e573df81`, runner exit 0 and unchanged source records. The 626.671265229-second configured full-suite duration is not subject to the native collector's 600-second limit.
- All 14 supplied CI instances / nine distinct checks: SUCCESS on the exact head. ROUTE run 38892452461 and CONTRACT run 38892452469 are successful attempt 1. I audited supplied CI metadata; I did not independently rerun or freshly query Actions.
- Pure native reductions recomputed against local frozen source returned no errors. ROUTE digest: `d801d663421733f8a97dee9cd5370eabf88829d3eef2ed09c8391e9b56aadad3`; CONTRACT digest: `b71046939e33f79f0198f4e21bfdab640a15ec9a6d548cb1d64444c18e408b52`. All six downloaded receipt hashes and run identities match.
- ROUTE: 12,283 assertions/platform, zero failures/errors/skips. CONTRACT: 322 tests/platform, zero skips, successful named checks; its absent failure/error counters were not invented.
- Native collection Linux/macOS/Windows: 283.233 / 300.018 / 272.095 seconds. **macOS exceeds the published 300-second target by 0.018 seconds and remains flagged.** All meet the unchanged 600-second limit. Cold CLI: 0.608 / 0.524 / 0.542 seconds, within the separate five-second product deadline. No waiver is inferred.
- Every supplied HTTP receipt row and all 2,445 per-input log summaries reconcile: 14,670 executions, 2,445 IDs / 1,859 distinct texts, 3,296 requests, 11,374 pre-effect rejections, zero violations on those inputs. All 582 designated positive boundary rows explicitly report true marker preservation. The computed-comment case rejects before effects at all six boundaries. Receipt/input/reviewer hashes match the brief exactly.
- All 20 input-provenance files match their recorded hashes. All prior 840 reviewer IDs are exact; the 128 added round-13 inputs are exact after the documented synthetic-sentinel substitution: Astra 44, alternative 41, failed correctness partial evidence 27, Grok 16. This supplies no vote for a failed task.
- Matrix preservation holds per format/label and per exact-string rejection permission against the 211-, 191- and 173-format sources; scheme folds are unchanged. Current 233 × six = 1,398 generated rows, comprising 1,228 distinct strings. The older row counts are 1,266 / 1,146 / 1,038; those must not be confused with distinct-text counts.
- All 147 SDK files are tracked. Current supplied full/native proof includes generation, strict schema/Node parity, offline packaging and installed CLI checks. I inspected package tests and manifests; I did not install dependencies or rebuild packages in this seat.

`audit.json` and `supplement.json` preserve independent calculations. The audit's initial `strings` fields count distinct texts; the supplement explicitly records both row and distinct counts.

**Original M1–M5 disposition**

| Criterion | Current disposition |
|---|---|
| M1: plans/interfaces/CLI/dependencies/SDK/bounded execution | Approved discovery/route and offline HOST/LEARN/EXPERIMENT boundaries are coherent; 147 SDK files and strict publication proof are present. Explicit unsupported modes and operational prerequisites remain. No additional demonstrated blocker beyond the supplied-context defect. |
| M2: privacy, durable authority, replay/recovery/deletion | **Not met: ALT-R14-1.** Earlier spending/provider/profile and durable-state repairs hold under source review, targeted tests and bound proof. Their success does not waive disclosure. |
| M3: exact-head packaging/offline/native proof | Current supplied evidence and pure reductions validate. Companion configuration is explicit in external `candidate1/verify_frozen.py`; no standalone or production companion acceptance is invented. macOS target flag remains visible. |
| M4: preserve stopped study/grants/unrelated trees; separate software and empirical acceptance | Preserved operationally: no real study/grant/provider, credential/private/holdout/raw-stream/hidden-reasoning access, sibling mutation, deployment or adoption. I inspected public material only and make no claim to have inspected private study contents. |
| M5: concrete criterion-backed findings | ALT-R14-1 has the existing criterion, exact source, trigger, actual HTTP/retention reproduction and minimum repair above. Suggestions remain suggestions. |

**Disposition of prior objections and requirements**

“Closed” below means the reported software reproduction is addressed on this head, supported by source, current exact-input replay/bound receipts and applicable independent tests. It never converts an old vote or execution into current approval.

| Prior item | Disposition |
|---|---|
| Scoped F1/R1 missing usage; zero/equal/conflicting counters; unknown cost | Closed: contract-valid `not_reported`, retained known/zero counters, immutable replay and no double dispatch. Unknown cost remains unacceptable empirical telemetry. |
| F2/R2 selected projection and menu/pricing leakage; F3/R3 nondiscriminating Boolean test | Closed: allowlisted selected profile, exact instruction combinations, independent forbidden-field assertion, and discriminating false/true controls. |
| F4/R4 required/optional baseline guidance | Closed to the approved exact task-required/retrieved rule, not an invented universally empty-required rule. Isolated optional-clause control remains. |
| F5/D1 and V2-1–4; fixture binding; O1/O2 | Closed: new v2 dispatch, historical v1 parse/replay, template/projection/field/rendered-request/cache/profile bindings, bound fixtures, independent pricing/menu guard and repeated native contract proof. |
| F6/D3 cheapest re-derivation, F7 duplicate study IDs/metric rows, D2 attribution order, D4 abstention, D6 offline alignment/two-resource coverage | Still unratified study-design/hardening concerns. No additional demonstrated merge blocker or empirical acceptance inferred. D5 provider authorization is separately repaired below. |
| F8 request-size estimate, F9 excerpt/tool-limited approval; timestamp identity/manual projection versioning/wire-parity observations | Limits remain accurately scoped. F8 lacked a demonstrated trigger; F9 never became a reliable approval. No new required feature inferred. |
| MERGE round 1 SDK omission | Closed: all 147 outputs, including the four patch modules, tracked and covered by exact-head packaging/generation proof. |
| Task provider allowlist / inherited D5; round 2 injected discovery authority | Closed: Application gates both adapter paths before effects; allowed/denied actual-adapter tests pass. Local/cloud/enabled/provider/hard-output restrictions retain precedence. |
| Portable recovery replenishment | Closed through permanent project/workspace admission blocking before preparation and inside admission transaction. Ledger restoration/reconciliation is not claimed. |
| Terminal deletion, recoverable SQLite bytes, imported tombstones | Closed: shared purge, cancel-pending for terminal workers, secure deletion/DELETE journaling/VACUUM, retained charges and no redispatch. Both actual synthetic direct/imported worker controls pass. |
| Discovery retention and deletion | Closed: artifact lifecycle association, archive/expiry/retry and objective deletion preserve independent task lifecycle. Portable-v1 raw discovery omission remains explicit. |
| ROUTE companion selection; downstream missing 10/30/31 controls; stale command fixtures; parameterized control identities | Closed in current collector/reducer structure and tests. Standalone ROUTE remains independent; installed companion requirements remain explicit. Historical collector timeout/skips are not passes. |
| Windows LF source drift; artifact namespace; transient native failures | LF setup and native-artifact-only selection remain; current source digests match all platforms. Earlier Windows failures/timeouts retain their outcomes and unestablished causes. Diagnostic reruns are not repairs or substituted successes. |
| Floating-point omitted overhead | Closed: producer and validators share `objective_duration`; no epsilon or tolerance relaxation. |
| Round 3 injected ceilings/model/counter | Closed by explicit scope removal for every new injected request ceiling, including funded requests, and pre-effect model/counter binding. Built-in verified pricing remains; execution caps stay distinct from judgment caps. |
| Rounds 1–5 Bearer/Basic, quoted/direct/JSON name-value, scheme-independent headers, folds/trailing whitespace/multiword values, duplicates/collisions/trimmed names, encoded strings | Exact reported forms closed; shared label and sibling rules present. Broader privacy criterion remains blocked by ALT-R14-1. |
| Presidential YAML/Python/assignment/header-pair/alternate member-name cases; recursion/quadratic concerns | Exact inputs close through sanitization or controlled rejection; node/work/deadline limits and resource-error conversion exist. The handle-or-reject structural requirement remains incomplete for the new recognized-whitespace cases. |
| Round 6 alias/reverse-reference/merge/tag graph loss, arbitrary member order/names, escaped labels, parser-omitted comments, credential keys, multiline assignment and ordinary-word cost | Exact cases closed. YAML graph support remains explicitly rejected; originals are inspected before lossy rewriting. |
| Round 7 prefixed strings/call RHS/augmented operators/escaped targets/non-scalar keys/Unicode indentation/leading-whitespace cost | Exact cases close, ordinary controls survive. The new composition with next-line computed scalar validation is not covered by their historical closure. |
| Round 8 adjacent literals/implicit tuple-attribute-subscript targets/bare CR/original-label loss/continuation work/MemoryError | Exact cases close; parser failures and bounded work retain explicit behavior. Native timing diagnostic changes did not relax product assertions. |
| Round 9 mixed separators/dash-only YAML/constant addition/formatted fragments/standalone schemes/incomplete private keys | Exact cases close. The prior omitted-dash fast-path failure remains historical; no rewrite of its outcome. |
| Round 10 inline computed records/numeric or unresolved expressions/early structured return/large YAML composition | Exact cases close; common original-source checks, input-relative work caps and 10,000-node deadline-aware composition remain. |
| Round 11 apostrophes/outer quoting/comments/fences/encoded association/scalar and keyword records | Exact required cases close. Astra provider failure supplied no vote. Computed-comment rejection and ordinary comments are separately verified. |
| Round 12 quoted physical folding/mixed sequence and plain scalar/spaced-parenthesized calls/offsets/invalid Store targets | Exact cases close. Failed native candidates, interrupted runs, public-control failures and obsolete external comment assertion retain their original failures. Grok's historical incomplete-reading limitation is not inherited here. |
| Round 13 ASTRA-R13-1 and partial C13-C1 quote escapes | Exact saved cases close, including ordinary escaped controls. The correctness task failed; its draft DISAGREE is not a vote. |
| Round 13 ASTRA-R13-2 / ALT-R13-1 next-line and explicit keys | Exact saved cases close. ALT-R14-1 demonstrates the still-open structural class with already recognized indentation/line-boundary composition. |
| Round 13 Grok B1 placement; B2 comments; B3 quoted-key detachment; B4 formatted/computed target bases | Exact saved cases close. The current fallback parse-success assumption remains insufficient under ALT-R14-1; no supplied expression executes. |
| Positive-proof precision and matrix preservation | Current 582/582 explicit marker assertions validate. Old 324 dispatches / 210 explicit markers / 114 nulls remain unchanged; Astra's separate 114-marker replay is supplemental only. No format/string/rejection permission was removed. |
| Round-14 development failures | Initial overrejection after 2,806 passes and subsequent 2,815/3,067/756/3,142/792 outcomes remain developmental, not replacement frozen proof. Failed hash/path invocations and failed-seat partial commands remain failures. Immutable report EOF warnings remain; source/test/readiness whitespace pass is not a whole-diff pass. |

**Separate presidential requirements**

The round-5 president's structural requirements were individually assessed: (1) common credential-label rule is present; (2) pair-preserving/recursive decoding is present, but it recursively carries ALT-R14-1 through encoded forms; (3) sibling masking is present for recognized parsed records; (4) complete free-text values/folds and ordinary following-line controls remain; (5) other formats must sanitize or reject before effects—**fails ALT-R14-1**; (6) generated labels × formats × six-boundary tests and ordinary positives exist, but their current input set misses this composition. Secondary depth/work controls are present. Clean full-suite and exact-head CI proof are now supplied and independently bound; that does not erase historical seven-error/full-suite failures.

Four fresh usable AGREE votes and a new separate tools-enabled president after all seats finish remain unmet prerequisites. This dissent prevents claiming unanimity. The previous separate Opus 5.5 `BLOCK_MERGE` remains binding. Owner authorization beyond the former cap waived no invariant. No source change, cancellation of another seat or carried vote is requested or implied.

**Suggestions and honest limits**

The nine earlier exclusions—correctness multiline-comment and encoded-mapping association; Grok inline-comment/value and next-key/comment; unquoted tuple, OpenPGP, colonless, unlabeled call and XML—remain suggestions. Round-13 comparison-target and blank-line cousin observations also remain suggestions. No passing HTTP claim covers them. Homoglyph/zero-width observations do not create new goals. ALT-R14-1 instead composes explicitly recognized indentation/line forms with an already required static credential-label check.

A consistent validation representation across parsed and fallback paths would make this boundary easier to defend, but a wholesale rewrite is not a new merge requirement. The minimum repair above is sufficient in scope; documentation narrowing is not a repair.

No full-suite, shared HOST/companion or native-host rerun, dependency install, nested agent, source/index/tracked-evidence edit, GitHub comment/watch or outward publication occurred. The PR is registered with this thread and is not watched. Package/native/full-suite executions are supplied proof, not my own runs. No empirical quality, calibration, phase completion, new collection, consumed-grant reuse, promotion or runtime-adoption authority follows.

One read command initially guessed `scripts/verify_frozen.py` and exited 2; the external candidate path was then located and read. It was not counted as a verification pass. Truncated displays were reread or explicitly treated as diagnostic summaries with complete saved data. The failing HTTP assertion remains visible. Final HEAD/status/index/all-source checks are unchanged and successful.

DISAGREE
