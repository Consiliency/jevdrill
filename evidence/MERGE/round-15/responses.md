# Round-15 combined response — Consiliency/jevdrill#1

All four round-14 tasks reached terminal states before the combined edit.
Correctness returned AGREE; Astra, alternative and Grok returned DISAGREE on
`b5b4796324324d6e7518be3f0e9faf5bc9d50ae3`, manifest SHA256
`57d11a17c8693a65f23ddd6c1631c2b27349a7443f519892a45b355671378986`
(824 files). Their complete reports remain byte-for-byte in
`evidence/MERGE/round-14/{correctness,astra,alternative,grok}.md`.
Correctness's passing corpus does not negate the other seats' demonstrated
counterexamples. No historical vote carries forward to edited source.

## Findings and repair

1. **Astra ASTRA-R14-1: unindented comment-only lines detached scalar members.**
   A column-zero comment between `name:` or `?` and an indented computed label
   ended fallback extraction. Ten inputs produced 60 wire / 50 raw disclosures
   over six boundaries; root independently confirmed the association loss.
   Structured continuation spans now retain comment-only lines at any indentation.
   The existing parenthesized validation preserves their physical comment scope.
   Ordinary free-text continuation behavior retains its separate grammar.

2. **Alternative ALT-R14-1: recognized indentation failed Python parsing.**
   VT/NBSP indentation was recognized as a continuation but passed unchanged to
   the Python validator, whose parse failure skipped the expression. Four plain
   examples and their JSON-string/log-object forms produced 72 wire / 60 raw
   disclosures. Root independently confirmed all twelve forms. Structured
   validation now normalizes recognized leading whitespace to equal-length ASCII
   spaces in its validation view, including sequence token views. Retained
   ordinary text is not rewritten. Line boundaries remain physical boundaries;
   supplied expressions are never executed.

3. **Grok GR14-1: unmatched quotation hid computed members.**
   Four unclosed/escaped-close records produced 24 wire / 20 raw disclosures.
   Malformed-document fallback now inspects incomplete quoted members at mapping
   and explicit-key indicators before fragment extraction. Apparent single-quote
   closers inside a computation cannot suppress the check. Decoded multiline
   quoted scalars also receive parenthesized member validation, covering bare
   explicit-key computations while preserving ordinary MIME records. Complete
   quoted values retain their existing structured sanitization path.

These repairs implement existing M2/EC-ROUTE-4 and the presidential original-member,
lossless-decoding and handle-or-reject requirements. No credential vocabulary,
provider, authority or empirical acceptance criterion changed. All earlier
nonblocking exclusions remain suggestions. Grok's comparison target, blank-line
cousin and unindented next-line observations remain suggestions, with no new
required goal or passing HTTP claim. A lossily truncated diagnostic that omitted
the sentinel is not privacy proof.

## Preservation and verification

Twenty-three appended formats cover all six existing supplied-context boundaries,
including encoded unclosed records. The matrix now has 256 formats / 1,536 strings.
Per-exact-string comparisons preserve all earlier formats, strings, rejection
permissions and standalone scheme folds: 233/1,398, 211/1,266, 191/1,146 and
173/1,038. Nine ordinary exact-text controls cover comments, recognized indentation,
unclosed quotes and doubled-apostrophe literal addition.

All 968 earlier reviewer IDs remain exact. The next HTTP corpus adds every saved
round-14 HTTP input: Astra 34, alternative 24, correctness 30 and Grok 9, totaling
1,065 reviewer IDs. Grok's cases were extracted from only the named literal
assignments in its inspected probe; its HTTP module was not imported/executed.
Only the synthetic sentinel spelling is normalized when adding these new inputs;
source hashes and provenance remain external. Direct replay found no disclosure
and preserved all 91 designated reviewer-positive markers. The next actual HTTP
probe explicitly checks every designated ordinary marker, including earlier
markers; historical receipts remain unchanged.

The expanded context/CLI/deadline/verifier batch initially passed 3,425 tests;
the final source with the additional ordinary regression passed 3,426.
The new six-boundary selection passed 828 tests (8,812 deselected). Scoped lint,
format, types, vocabulary, vocabulary lint and import checks passed. Development
runs do not replace the new frozen-head full, native and actual HTTP proof.

## Retained development failures and evidence limits

The first raw-quote guard rejected a supported complete JSON Digest value:
the small first context invocation ended with 1 failure / 45 passes. Restricting
that path to incomplete/malformed quoted members restored all 3,078 existing
context tests. A later direct replay rejected two ordinary escaped Content-Type
records because bare-member validation treated their MIME slash as a computation.
Parenthesized validation restored both without dropping any input or positive
assertion; a focused ordinary regression was added. The final local rerun is
recorded externally before the new freeze. An initial external-script import
failed because the repository was absent from its module path; setting PYTHONPATH
fixed invocation. Another preparation attempt treated Grok's LATEST_SEAT.txt as a
directory; explicit directory selection fixed that invocation. A format check
reported one file needing formatting, which was formatted before final checks.
All failed outputs remain external and are not claimed as passes.

Round-14 proof remains scoped to its original head and tested inputs: 12,781 full
tests, 12,283 ROUTE and 322 CONTRACT native tests per platform, nine distinct CI
checks and 14,670 root HTTP executions. It did not cover the new counterexamples.
The macOS 300.018-second collection exceeded the 300-second proof-cost target
and retained its flag; it satisfied the unchanged 600-second collection limit.
Neither measurement is the five-second product deadline or configured full-suite
duration. No flag is rounded away or waived. Independent review execution and
reading limits remain as stated in each report, including Grok's historical
compressed-section and initial composer-path invocation limits.

The successor requires fresh unchanged-head full, native and actual HTTP proof,
then four fresh usable AGREE reviews, then a separate tools-enabled Opus 5.5
presidential ruling. The round-5 BLOCK_MERGE remains binding until those conditions
are satisfied. Continuing beyond the former cap waived no invariant. No admin or
force merge, deployment, promotion, real provider/study/grant/holdout activity or
empirical acceptance follows. Unrelated dirty worktrees remain preserved.
