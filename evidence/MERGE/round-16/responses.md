# Round-16 combined response — Consiliency/jevdrill#1

All four round-15 tasks were terminal before any edit. On
`6862eb88dc849f8b0114de9d2418c1fe4ec3bc27` (829 files; manifest SHA256
`cd19163bc6b6dc9feb2e5e910e3b63cc9b7b27907190a2f51feb709a0f47c4e8`),
correctness completed AGREE, alternative and Grok completed DISAGREE, and Astra
FAILED with a provider cybersecurity-risk flag and no standing vote. Complete
reports remain byte-for-byte in `evidence/MERGE/round-15/`. The exact Astra task
failure is in `astra-provider-failure.json`; no report was produced. Its eight
saved direct observations are explicitly partial in `astra-partial-diagnostic.json`.
No request was retried, rephrased or routed to another provider to evade the flag.
The fresh source repair responds to independently confirmed product behavior.
Correctness's clean corpus does not negate the other seats' counterexamples.
No vote carries to edited source.

## Combined findings and repair

1. **Alternative ALT-R15-1 and Grok GR15-B: inconsistent validation views.**
   Quote decoding left NEL/Unicode physical separators and NBSP/VT indentation
   for Python to reject as syntax; interior NBSP/VT had the same effect. Failed
   parsing skipped the member. Alternative's four shapes, each plain/JSON-string/
   JSON-log encoded, produced 72 wire /60 raw disclosures. Grok's three interior
   whitespace forms produced 18 /15. These are separate executions, not a count
   of distinct defects or inputs to add together. Root checked receipt/input/
   report hashes and independently reproduced every direct form.

   One shared validation-view helper now normalizes recognized physical breaks
   to LF and recognized whitespace to ASCII spaces, with deadline checks. It is
   applied after quote decoding, to scalar/sequence fallback and AST expression/
   target views. Retained ordinary source bytes are unchanged. Physical comment
   boundaries and original sibling associations remain intact.

2. **Grok GR15-A: false closers before a newline.** Three inputs produced
   18 wire /15 raw disclosures. A short quoted match ending inside `str(` was
   skipped because its next character was a line break. The closed-member path
   now validates the original quoted body; incomplete computed members reject
   before effects. Multiline quoted members use their decoded representation.
   A complete quoted scalar is not reinterpreted as unescaped Python source after
   successful validation. Quote discovery still considers unescaped placements;
   doubled apostrophes in an already validated multiline YAML scalar are escapes,
   not independent openers spanning unrelated literals.

3. **Grok GR15-C: inline Markdown around a scalar.** One input produced
   six wire /five raw disclosures. Record-member validation now inspects the
   content of inline backtick spans, including incomplete spans, using the same
   bounded validators. Ordinary public Markdown retains exact-text controls.

4. **Failed Astra seat's partial diagnostic: quote on a following line.**
   Root independently confirmed eight direct sentinel survivors. These are not
   eight HTTP-tested inputs or a review vote. Malformed quoted-member discovery
   now retains whitespace, physical lines and comment-only lines between the
   member indicator and opening quote. Unresolved `chr(...)` compositions reject
   without executing them. The eight exact partial inputs are included in the
   successor's proof with their explicitly partial provenance.

These implement M2/EC-ROUTE-4 and the president's original-member, lossless-decoding
and handle-or-reject requirements. No provider authority, credential vocabulary,
deadline, node/work bound or acceptance invariant was relaxed. Grok's comparison,
blank-line and unindented-next-line observations and every earlier explicit
exclusion remain suggestions; no new goal or passing HTTP claim covers them.

## Ordinary preservation and development outcomes

The first repair passed all 3,363 existing context tests and removed sentinels from
the saved round-15 inputs. Adding ordinary controls and the complete replay exposed
regressions: the first expanded context/CLI batch had one failure /3,747 passes,
and replay rejected four positive IDs. Enclosing complete multiline expressions
restored the ordinary double-quoted addition; that intermediate batch passed
3,748 tests. Two new single-quoted ordinary controls then failed (2 failures /
3,748 passes), matching two imported alternative-positive IDs.

The cause was layered syntax: decoded public constant expressions were checked,
then YAML's doubled apostrophes were scanned again as independent quote openers
or unescaped Python. Several partial development repairs still failed those four
IDs; their separate failed replay receipts are retained externally, including
the changed incomplete-member error. None is a privacy pass.

Static literal analysis now also recognizes `str` with exactly one constant
string argument and no keywords as that same string. It executes no supplied
call and does not accept arbitrary call arguments or functions. Complete resolved
public constant expressions retain source bytes after their resulting string
passes credential checks. Credential results still reject; unresolved computations
still reject. Validated quoted scalars avoid the redundant escaped-source parse.
Twelve ordinary exact-text controls cover decoded additions, LS/NEL, VT/NBSP,
Markdown, unclosed public quotes and static call-valued assignments.

The final direct replay passes all 2,966 input IDs /2,336 distinct texts and all
163 designated ordinary markers. All 1,065 earlier reviewer IDs remain exact.
Added inputs comprise correctness 66, alternative 22 and Grok 13 actual saved
HTTP inputs, plus the failed Astra seat's eight direct-only diagnostics: 1,174
reviewer IDs total, with all 115 reviewer-positive markers preserved. The base
positive set grows from 36 to 48. Only newly imported synthetic sentinel spellings
are normalized; hashes and provenance identify original sources.

Twenty-six appended formats cover six labels and all six existing boundaries.
The matrix now has 282 formats /1,692 strings. Per-exact-string comparisons retain
all prior 256/1,536, 233/1,398, 211/1,266, 191/1,146 and 173/1,038 strings AND actual
rejection permissions, labels and scheme folds. No failed input or positive
assertion was pruned. Final local context/CLI/deadline/verifier checks passed
3,750 tests; the new six-boundary selection passed 936 (9,640 deselected).
Scoped lint, format, types, vocabulary, vocabulary lint and imports passed.
Outcomes are recorded externally before committing; none substitutes for new
frozen-head proof.

## Evidence limits and remaining gates

Grok's complete diagnostic had 78 executions, 42 wire /35 raw disclosures and
zero DB hits; exit 0 meant diagnostic completion, not privacy success. Its initial
wrong-directory manifest check and invalid backslash-text diagnostic remain
invocation failures. Alternative's 132-execution HTTP check exited 1 on its
unchanged privacy assertion; later assertions in that script were not reached.
Root separately checked all 36 positive markers and 24 normalized zero-effect
rejections against that saved receipt. Correctness's 396 independent HTTP
executions and passing state/authority batches remain scoped to its tested corpus.
Complete-reading claims and each seat's limitations retain their report scope.

The old root's 13,894 full tests, 16,134 HTTP executions, nine CI checks and native
13,396/322 tests per platform passed only on their original head and input sets.
They did not cover these new disclosures. All three native collections retained
their 300-second proof-cost target flags (309.377/342.436/398.448 seconds) and met
the unchanged 600-second collection limit. Those are distinct from the five-second
product deadline and 670.605-second configured full-suite command. No waiver or
rounding changes these facts. Historical failures remain failures.

The successor requires fresh unchanged-head actual HTTP, configured full-suite
and native proof, then four fresh usable AGREE reviews, then a separate
tools-enabled Opus 5.5 presidential ruling. The old round-5 BLOCK_MERGE remains
binding. Owner continuation beyond the former cap waived no invariant. There is
no admin/force merge, deployment, promotion, real provider/study/grant/holdout
activity or empirical acceptance. Unrelated dirty worktrees remain preserved.
