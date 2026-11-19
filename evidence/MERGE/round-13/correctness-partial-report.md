**Correctness seat — full-PR review of Consiliency/jevdrill#1**

**Do not merge this candidate.** I independently reproduced one P1 credential-disclosure blocker on frozen HEAD **cb2ab89725503b044b79e5ef691910b2e563e4c3**. Valid YAML quote escaping bypasses original-line validation: eight inputs disclosed their synthetic sentinel over actual local HTTP at all six supplied-context boundaries. This is a fresh board-seat review, not the separate president’s ruling. No earlier vote carries.

Report and independent artifacts: `/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/`.

**Binding and complete reading**

Every repository operation explicitly used `/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed`. Before and after review, HEAD matched, worktree status was empty, the index was clean, and all 818 source hashes matched. The final tracked path set exactly matched the manifest. The required command, run from the actual root, exited 0 with no output before and after:

    sha256sum --quiet -c /mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/candidate1/source-manifest.sha256

Independent Python hashing also checked every file. See [before.json](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/before.json) and [after.json](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/after.json).

- Source manifest: 96,196 bytes; SHA256 `490a3961f379579bbcc2bd6278bcadfa55bd2b533500c38bac5d96889bd10cfe`.
- Complete packet: 630,074 bytes; SHA256 `f71ddb437ae8f795dde0a9e83201146ed5c96a79147db92a9c5fdaf0503ebfff`.
- I read the entire packet, including every nested historical narrative, in 22 untruncated chunks. The first round-13 header governs; historical headers, pending statuses and votes retain their original scope.
- I separately read all 6,688 bytes of `evidence/MERGE/round-13/responses.md`, SHA256 `68d3c3b41d2028ff9eb4b72f9994a8b8ca85fa9d3b54961554ac7ebe5a5859d2`, and all 12,633 bytes of `evidence/MERGE/round-5/president.md`, SHA256 `dec30810d6f80afa2f62bf365e46a35c08fe393d639350982f0857bbb3efd9b7`.

The packet ledger uses byte offsets, start inclusive/end exclusive:

| Chunk | Start | End |
|---|---:|---:|
| 1 | 0 | 22000 |
| 2 | 22000 | 52000 |
| 3 | 52000 | 82000 |
| 4 | 82000 | 112000 |
| 5 | 112000 | 142000 |
| 6 | 142000 | 172000 |
| 7 | 172000 | 202000 |
| 8 | 202000 | 232000 |
| 9 | 232000 | 262000 |
| 10 | 262000 | 292000 |
| 11 | 292000 | 322000 |
| 12 | 322000 | 352000 |
| 13 | 352000 | 382000 |
| 14 | 382000 | 412000 |
| 15 | 412000 | 442000 |
| 16 | 442000 | 472000 |
| 17 | 472000 | 502000 |
| 18 | 502000 | 532000 |
| 19 | 532000 | 562000 |
| 20 | 562000 | 592000 |
| 21 | 592000 | 622000 |
| 22 | 622000 | 630074 |

[read-ledger.jsonl](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/read-ledger.jsonl) records each chunk’s path, offsets and hash. Coverage is contiguous and complete. Supplementary broad source/search output sometimes truncated; relevant source portions were reread in smaller ranges. Those searches followed the complete packet read and were not substitutes for it. I did not line-audit every generated file or every historical artifact outside the packet.

**C13-C1 — P1: YAML quote escapes bypass original multiline record validation**

Broken requirements: M2; [sanitization before submission/persistence](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/plans/phase-plan-v1-ROUTE.md:220); [EC-ROUTE-4’s sent/retained-sentinel falsifier](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/plans/phase-plan-v1-ROUTE.md:410); and the [original-quoted-line guarantee](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/docs/route-readiness.md:86). This also prevents closure of the president’s lossless interpretation, sibling sensitivity and handle-or-reject requirements. It concerns the quoted-record association already in scope, not an excluded cousin-association suggestion or new credential vocabulary.

This is valid YAML, with a physical line break:

    'name: ''Author''+''ization''
    value: SYNTHETIC_R13_CORRECTNESS_SENTINEL'

Its exact Python construction is:

    text = "'name: ''Author''+''ization''\nvalue: SYNTHETIC_R13_CORRECTNESS_SENTINEL'"

On this HEAD, `redact(text) == text`. YAML interprets doubled quotes as literal single quotes, then folds the line break:

    name: 'Author'+'ization' value: SYNTHETIC_R13_CORRECTNESS_SENTINEL

The quote-decoded record with its original line break retained correctly rejects:

    name: 'Author'+'ization'
    value: SYNTHETIC_R13_CORRECTNESS_SENTINEL

At [context.py:328](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/context.py:328), the new guard removes only the outer delimiters (`original = text[1:-1]` at line 336). It does not interpret YAML quote escapes while retaining original boundaries. Both the [line-start scan](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/context.py:191) and [quoted scalar-token check](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/context.py:250) reach this incomplete guard. YAML composition then folds the boundary; [context.py:315](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/context.py:315) receives no reported change and returns the original bytes at lines 317–319.

I reproduced eight valid-YAML variants: Authorization and X-API-Key labels; static string addition and unresolved `str(...)` computations; single-quote doubling and double-quote backslash escaping. No supplied expression was executed. All eight escaped forms passed unchanged; all eight decoded, line-preserving controls rejected.

The [HTTP probe](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/http/probe.py), [inputs](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/http/inputs.json), [receipt](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/http/receipt.json), and [parser trace](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/quoted-scalar-trace.json) preserve the reproduction. Each execution used fresh external storage, synthetic scope/allowance, fake inline credentials and a loopback DevelopmentJudge endpoint.

| Boundary | Leaking inputs | HTTP disclosures | Raw-artifact disclosures |
|---|---:|---:|---:|
| Route task | 8 | 8 | 8 |
| Route attachment | 8 | 8 | 0 |
| Discovery objective | 8 | 8 | 8 |
| Discovery authorized context | 8 | 8 | 8 |
| Discovery description | 8 | 8 | 8 |
| Discovery attachment | 8 | 8 | 8 |
| Total | 48 boundary executions | 48 | 40 |

Each failing execution made one HTTP request and recorded one 2,753-microusd synthetic reservation. No sentinel was found in database files. Route returned `ready`; discovery outcomes varied, including `discovery_failed` after disclosure. Later non-success does not undo submission or retention.

**Minimum repair:** inspect quote-decoded content while retaining original line/record associations before YAML folding, or reject these ambiguous escaped multiline computed records before effects. Do not restore original bytes after losing associations. Cover both quote styles, static/unresolved expressions and all six boundaries while keeping ordinary escaped multiline text and Content-Type controls usable. Preserve existing deadlines, node budget, fixtures and rejection permissions. No execution of supplied code or expansion into excluded suggestions is required.

**Independent execution**

- **Focused repository suite:** 3,207 passed, zero failures/errors/skips, exit 0, runner 83.173 seconds. Coverage included privacy, discovery/route application, durable storage, retention, maintenance, experiment execution/development, adapters, CLI and pure verifier controls. It deselected 7,992 database-matrix cases; it was not a full-suite/shared HOST rerun. [Command](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/focused-command.json), [JUnit](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/focused.xml), [receipt](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/focused-process.json).
- **New regression suite:** 16 tests, **8 failed/8 passed**, zero errors/skips, exit **1**. Failures are escaped valid-YAML records; passes establish rejection of decoded controls. [Tests](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/test_quoted_scalar_regression.py), [JUnit](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/regression2.xml), [receipt](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/regression2-process.json). The first invocation exited **4**, with a collection PermissionError on `/mnt/workspace/users`. Its [error receipt](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/regression-process.json) is retained; only external rootdir/confcutdir was corrected. That invocation is neither a pass nor a product failure.
- **New actual HTTP:** 162 executions, 27 IDs/27 distinct texts, 13.929 seconds, 120 requests; **48 wire/40 raw disclosures**; 42 pre-effect rejections with no requests/artifacts/reservations; all **66 ordinary positive checks** dispatched with required markers preserved. Harness exit 0 means collection completed; recorded **privacy result is FAIL**. [Summary](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/http/summary.json). Receipt SHA256: `782510ab3e88fd925d32c15667b3068a35c73b72dbe57c99cdb435383936952a`.
- The HTTP set also exercised repaired mixed-sequence, folded-scalar, keyword, invalid-target and original unescaped-record controls. Exploratory direct inputs/results are retained separately; their counts are not added into a deduplicated execution total.
- **Exact-head archive:** all 818 matching files, all **147 tracked SDK files**; jevdrill/contracts/BAML SDK/TypeSafe patch/vendor imports resolved inside the extracted archive; 78 schema entries loaded. Existing dependencies only; no build/install. [Archive check](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/archive-check.json).
- **Evidence audit:** parsed every supplied full-suite test case, HTTP row and case-log entry; checked hashes, 20 recursive provenance-source hashes, retained inputs, complete Cartesian coverage, rejection effects and positives; independently ran only the **pure native reducers**. [Validation](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/independent-evidence-validation.json), [validator](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/validate_evidence.py), [provenance](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/provenance-validation.json).
- **Matrix preservation:** 211 formats/1,266 strings preserve all prior 191/1,146 exact strings and rejection permissions; separately verified earlier 173/1,038 and permissions. Standalone scheme folds are unchanged. [Earlier-matrix check](/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round13-20261016/reviews/correctness/seat-20261016T102445Z-af367846/round11-matrix-validation.json).
- An exploratory search named nonexistent `scripts/verify_contracts.py`; it was corrected to `scripts/verify_contract_phase.py` before pure reduction. No collector ran. A report-drafting tool call had a quoting syntax error and wrote nothing; the corrected report was then saved. Neither error is reported as a verification pass.

**Supplied execution, independently validated but not rerun**

| Proof | Checked result |
|---|---|
| Configured full suite | 11,725 tests; zero failures/errors/skips; exit 0; 638.1567067089927 seconds |
| Full JUnit SHA256 | `dfd128eacee055ca739f17e7f62ae26a1e99d407002f4b81f69d499826acac9c` |
| Root actual HTTP | 13,062 executions; 2,177 IDs/1,655 texts; 840 reviewer IDs; 3,020 requests; 10,042 pre-effect rejections; zero recorded violations |
| Positive controls | All 324 explicit checks dispatched; required markers preserved wherever specified; sensitive computed-comment control rejected at all six boundaries with zero effects |
| Reviewer preservation | Original 680 inputs retained exactly, plus 160 round-12 inputs |
| CI binding | Nine distinct workflow/check identities, 14 successful completed instances, exact HEAD |
| ROUTE native | Run 38884673592, attempt 1, exact HEAD; 11,227 tests/platform; zero failures/errors/skips; pure reduction has no errors |
| CONTRACT native | Run 38884673680, attempt 1, exact HEAD; 322 tests/platform; zero skipped; test commands exit 0; pure reduction has no errors |

Root HTTP receipt/input/reviewer-input SHA256 values respectively match:

- `c9a21c71e2f4f7678b03d2ff4ac464eabcccde8058cf8b1f0c8b8bc8dd034bf2`
- `5081827207de5faf10475dc57c0c5d6d97a33d9b9f702197c4e8723463eddf3e`
- `7115002f76a645d00cc89f23b29e3f69bbf9d0b9112fa80c39342800bd5bcc5e`

Recomputed native source digests: ROUTE `555235fbb9255437c4f6b024610909358ca22ea91165e955f832ec9a46ca6ab4`; CONTRACT `5ea4156c5d73b45242fc3ea2b04ff6ee60a43712fa4358d35d811b131413a38e`.

Native collection times are Linux **274.452**, macOS **325.022**, Windows **267.099** seconds. macOS explicitly flags exceeding the **300-second target**. All satisfy the unchanged **600-second collection limit**. Cold CLI durations are **0.639/0.688/0.551** seconds respectively. The five-second product deadline, native collection limit and full-suite duration measure different commands. No waiver is granted.

Root’s HTTP and full-suite executions were sequential, HTTP first. Their before/after receipts bind clean unchanged source. These proofs support those executions; they do not refute C13-C1. I did not rerun the full suite, native hosts, shared HOST collector or companion installation. Root explicitly configured the companion root/interpreter; missing them would be an invocation error.

**Original M1–M5**

| Requirement | Disposition |
|---|---|
| M1: approved plans/interfaces, ROUTE discovery/task routing, offline HOST/LEARN/EXPERIMENT, durable CLI, dependency/schema/SDK publication and bounds | Source/interface review, focused checks, archive imports and native evidence support the published architecture/bounds. No additional M1 blocker reproduced; completion remains blocked by M2. |
| M2: durable replay/recovery/idempotency, privacy/retention and fail-closed authority | **Not met: C13-C1.** Supported authority/storage repairs do not excuse disclosure. |
| M3: exact-head packaging/offline/native proof and honest prerequisites | Current evidence and independent hash/reducer/archive checks support this, with macOS target flag and companion limits disclosed. No separate M3 blocker reproduced. |
| M4: preserve stopped study/grants/dirty worktrees; no empirical acceptance | Preserved. No private study/holdout, secrets/auth/.env, raw-stream or hidden-reasoning reads; no real provider/grant use, restart, preview enablement, deployment, promotion or adoption. |
| M5: invariant, source location, trigger/consequence, executed reproduction and minimum repair; suggestions stay separate | C13-C1 meets this standard. Historical failures remain failures; no assertions/deadlines relaxed or unsupported suggestion promoted. |

**Inherited objections and repairs**

“Reported trigger repaired” below is limited to current controls/evidence; it does not mean universal parser correctness.

1. **R1–R4:** valid unknown telemetry/immutable replay; selected-configuration projection without pricing/unselected menus; discriminating false/true suitability; exact required/retrieved baseline guidance with optional baseline guidance forbidden remain supported. Actual stopped private-record compatibility beyond synthetic fixtures is not claimed.
2. **D1 and pre-freeze binding:** new JudgeCandidate-v2 dispatch versus parseable immutable historical v1 replay; rendered-request/template/projection/profile/cache binding; source-bound fixtures and isolated optional-guidance controls remain supported. Manual projection-version discipline and verification-timestamp identity retain stated limits.
3. **O1/O2/publication:** independent forbidden pricing/menu assertions and native OS evidence remain present. The original four missing SDK files are tracked; all 147 SDK files are archive-importable. Historical generation/package failures remain failures.
4. **Provider authority, including D5:** task/discovery enabled/cloud/local/provider/allowlist restrictions and supported output-limit gates precede dispatch. Empty provider lists retain documented meaning. Synthetic adapters confer no real authority.
5. **Spending/model/counter/profile authority:** all explicit injected request spending ceilings, including funded ones, reject before preparation/reservation/dispatch. Separate study allowance is not request-ceiling authority. Built-in ceilings require verified input pricing/zero output rate; unsupported output enforcement rejects. DevelopmentJudge’s pinned `jev-1.13.0` and supported counter are checked; ordinary built-in `jev-latest` is distinct.
6. **Durable experiment/replay/recovery:** immutable identities, CAS transitions, transactional allowance aggregation, reservations retained on uncertainty, no redispatch on lost acknowledgment, worker custody, cancellation and cleanup remain supported. Portable-v1 omits experiment ledgers/dispatch identities and persistently blocks new admissions after import, before preparation and transactionally. It does not reconcile or replenish a grant.
7. **Deletion/retention/raw discovery:** completed-worker cancellation scrubs payloads with secure deletion/DELETE journaling/VACUUM; direct/imported task tombstones share purge/cancellation; reservations stay charged. Objective-associated raw-content lifecycle, archive/expiry, retry/deletion invalidation and separate namespaces remain supported. Portable recovery omits raw discovery; local encrypted archival/metadata recovery have narrower documented guarantees.
8. **Downstream proof:** HOST/LEARN/EXPERIMENT control selection, required 10/30/31 coverage, parameterized identities, exact duration sums, LF checkout and artifact namespaces remain represented. No epsilon/deadline relaxation. Runner scratch storage improvement does not establish the cause of historical failures.
9. **Rounds 3–5:** quoted assignments, arbitrary schemes, complete/multiword values, CR/LF folds, blank/Unicode indentation, duplicate/colliding members, trimmed/prefixed labels, Postman/header pairs and encoded layers retain controls. Overall structural closure remains open through C13-C1.
10. **Round 6:** aliases/anchors/merge/tags reject; comment removal, credential scalar keys, mixed arbitrary-field/order associations, ordinary-word scaling and deep-nesting handling retain controls. Unsupported syntax is not permission to disclose.
11. **Round 7:** raw/bytes/formatted multiline strings, multiline call RHS, augmented statements, escaped/concatenated/continued targets, non-scalar YAML keys, NBSP/VT/FF blocks, whitespace scaling and deep braces retain repaired controls. Structured-key disclosure was a blocker on its historical head despite another seat’s suggestion label.
12. **Round 8:** implicit multiline/tuple/attribute/subscript targets and bare CR; adjacent literal mappings/keys/pairs; original associations before rewriting; continuation bounds and JSON MemoryError boundary handling retain controls. No current recurrence reproduced in selected checks.
13. **Round 9:** six line-ending families, dash-only sequences, constant additions/formatted fragments, standalone Basic/Bearer continuations and overlapping private-key scans retain controls, including ordinary following-line preservation.
14. **Round 10:** prose/Markdown placement, numeric/name/call/slice computations, nonmutating early-YAML validation, node/deadline bounds and 10,000-node cap retain controls. No new timing failure independently reproduced here.
15. **Round 11:** apostrophes/outer presentations, comments/fences, original encoded associations, YAML scalar/keyword records and attribute/conditional/boolean computations retain controls. Astra’s provider failure supplied **no vote**; root independently corroborated saved probes. Completed round-12 Astra DISAGREE is a separate usable report.
16. **Round-12 correctness C12-C1:** original unescaped multiline examples now reject; **the requirement remains open through C13-C1**, using valid quote escapes to reproduce fold-and-restore behavior.
17. **Round-12 alternative ALT-R12-1/2:** reported unresolved mixed sequences/folded plain scalars now reject. Complete continuation/per-member checks remain exercised; ordinary call-valued assignment RHS and MIME controls remain usable.
18. **Round-12 Astra:** spaced/tabbed/parenthesized keyword calls have callable/synthetic-prefix handling and passing controls. Both developmental AST-offset failures remain historical failures.
19. **Round-12 Grok:** invalid computed targets, including parentheses/prose/walrus/format variants, have rejection controls. I independently exercised representative triggers. Grok’s stated nested-history reading limitation remains a limitation of that report; I met complete reading independently.
20. **Matrix/ordinary preservation:** prior strings and rejection permissions remain unchanged with 20 appended formats. Positive multiline, Content-Type/MIME, keyword, mixed-sequence, folded text, signed-value, revision-ID, call-valued assignment and following-line controls remain supported. They do not cover the missing escaping cross-product.

Study-design questions **remain unratified, not declared repaired**: F6/D3 cheapest-feasible re-derivation; F7 duplicate study IDs/metric rows; D2 arm-order attribution; D4 abstention; D6 offline/two-resource alignment. I performed no new end-to-end forged-study acceptance experiment and establish no additional M5 blocker from those questions. F8’s request-size concern, projection maintenance, timestamp identity and stopped-record compatibility retain prior limits. No empirical criterion is waived.

Historical outcomes remain intact: d4cf native comment/offline revision-ID failures; interrupted -15/143 runs; bcf ordinary-MIME rejection; b2 external assertion failure and separate corrected execution; provider failure without verdict; timeout failures followed by unchanged narrow reruns; current two AST-prefix-offset failures, expanded single-quoted-multiline failure, then 2,815 context, 758 boundary and 63 CLI/deadline/verifier passes. A later pass does not rewrite an earlier failure.

**Presidential requirements**

| Requirement | Disposition |
|---|---|
| Unified normalized credential-label rule | Present for recognized labels; C13-C1 bypasses interpretation, not vocabulary. End-to-end closure remains unproven. |
| Lossless member/encoded-string handling; no restoration after lost associations | **Unmet through C13-C1.** |
| Sensitive scalar masks siblings regardless of names/order | Recognized cases pass; **unmet end to end through escaped records**. |
| Complete free-text folds/continuations with ordinary following text preserved | Preserved controls pass; no separate new free-text blocker. |
| YAML/Python/code handled or rejected before effects | **Unmet through C13-C1.** |
| Generated format×label×six-boundary tests and ordinary controls | Existing matrix preserved/execution verified; valid escaping cases demonstrate missing behavior/coverage. |
| Bounded parsing, clean full suite, nine exact-head checks | Current evidence supports these, with macOS target flag disclosed and limits unchanged. |
| Four fresh usable AGREE reviews, then new separate tools-enabled president on unchanged source | **Not satisfied.** This seat dissents. Separate Opus 5.5 **BLOCK_MERGE remains binding**. |

**Suggestions, limits and authority**

Correctness’s separately commented multiline code and nested encoded cousin association remain nonblocking. So do Grok’s unquoted tuples, OpenPGP, colonless prose, unlabeled calls, XML and two comment-only cousin associations. They remain excluded from claimed passing HTTP coverage. Homoglyph/zero-width normalization, other cousin associations and placement-specific assertions remain suggestions without a new invariant-cited reproduction here.

No nested agents, source/index/tracked-evidence edits, resets, commits, installs, mutating collectors, GitHub comments or watchers were used. Only fresh external synthetic evidence was written. Main, companion, real grants, stopped study and disabled/expired preview were untouched. The PR is linked and not watched. This vote neither releases the shared freeze nor authorizes merge, deployment, promotion, adoption or empirical acceptance.

DISAGREE

