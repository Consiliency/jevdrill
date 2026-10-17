# Round-14 combined response — Consiliency/jevdrill#1

All four round-13 tasks were terminal before source edits. Astra, alternative and
Grok completed with DISAGREE on `cb2ab89725503b044b79e5ef691910b2e563e4c3`,
manifest SHA256
`490a3961f379579bbcc2bd6278bcadfa55bd2b533500c38bac5d96889bd10cfe`
(818 files). Correctness terminated FAILED with a provider cybersecurity-risk
flag and no usable terminal review. Its exact error and null standing verdict
are retained in `evidence/MERGE/round-13/correctness-provider-failure.json`.
Its saved report/probes are explicitly partial evidence in
`correctness-partial-report.md`, assessed independently by root; the report's
draft vote does not override the task failure. No restriction was bypassed or
request rephrased to evade the flag. The three completed reports remain intact
beside that partial report. No historical vote carries forward.

## Findings and combined repair

1. **Astra ASTRA-R13-1 and correctness partial C13-C1: YAML quote escaping.**
   Removing outer delimiters did not decode doubled apostrophes or backslash
   escapes before YAML folded physical record boundaries. Astra reproduced
   48 wire / 40 raw disclosures; the failed seat's saved probe independently
   recorded 48 / 40. These are separate, overlapping executions, not totals to
   add. The quoted-member guard now decodes single-quote doubling or double-quote
   YAML escapes while preserving physical line breaks for recursive validation.
   Ordinary escaped multiline Content-Type records have preservation controls.

2. **Astra ASTRA-R13-2 and alternative ALT-R13-1: indented first content and
   explicit keys.** A bare `name:` or `?` line lost its following computed member
   during fallback extraction. Astra reproduced 24 wire / 20 raw disclosures;
   alternative reproduced 66 / 55 across next-line values, explicit keys, CR/CRLF
   and unresolved calls. Root independently confirmed the mixed/whole-document
   difference. Malformed-document fallback now retains complete original scalar
   spans, including empty first lines and explicit-key indicators. A synthetic
   parenthesized expression lets the existing bounded validator inspect physical
   continuations without flattening them first. Supplied expressions never run.

3. **Grok B1: quote placement.** Three placements produced 18 wire / 15 raw
   disclosures. Quoted-source discovery now considers quote positions throughout
   the original text, independent of line starts or preceding prose. Its work
   uses the existing input-relative bound and shared deadline. Tests include
   quotes after a key, indentation and an adjacent prose prefix. An opener cannot
   hide a later candidate merely by consuming it in a disjoint match.

4. **Grok B2/B3: comments and quoted-key detachment.** Commented folds produced
   18 wire / 15 raw disclosures; separately decoding a quoted key produced 6 / 5.
   Fallback scalar validation now sees the original comments and physical lines,
   before folding or JSON extraction can erase their associations. Parenthesized
   validation keeps Python comments confined to their original physical lines.
   Quoted keys remain attached to their original folded values during that
   validation. Ordinary public folds and comment text retain their controls.

5. **Grok B4: formatted targets and computed bases.** Three targets produced
   18 wire / 15 raw disclosures. Failed Store parsing now also rejects unresolved
   formatted, attribute and subscript expressions. Successful Store targets reject
   attribute/subscript bases that are computations instead of static name chains.
   Static targets, computed constant credential indices, call-valued RHS and
   ordinary following lines retain the existing controls. The repair executes no
   supplied computation. Grok's full probe recorded 60 wire / 50 raw disclosures
   across ten inputs; those counts overlap the family counts above.

These defects violate existing M2/EC-ROUTE-4 and the presidential original-member,
lossless-decoding and handle-or-reject requirements. The repair adds no provider,
credential vocabulary, study objective or new authority. All previously excluded
cousin/comment associations, unquoted tuples, OpenPGP, colonless prose, unlabeled
calls and XML remain suggestions. Grok's comparison-target and blank-line cousin
observations are also suggestions, not new required goals or claimed HTTP passes.

## Regression and proof preservation

Twenty-two appended formats exercise the existing six-boundary matrix, bringing
it to 233 formats / 1,398 strings. The prior 211 formats / 1,266 strings, their
rejection permissions and all standalone scheme-fold inputs remain unchanged.
The preservation checker explicitly compares rejection membership of each exact
string, rather than membership of format names; earlier source states also retain
independent reviewer preservation checks. Eight ordinary exact-text controls cover
escaped and inline quotes, next-line scalars/explicit keys, public comment folds,
static attribute chains and multiline call-valued assignment RHS.

All previous 840 reviewer IDs remain exact. The next actual-HTTP matrix adds all
128 saved round-13 HTTP inputs, including the failed seat's explicitly partial
inputs without inferring a vote. Direct replay of all 968 IDs found no disclosure
and preserved all 70 designated reviewer-positive markers. Input hashes and source
roles remain recorded externally.

The round-13 receipt's 324 positive executions all dispatched, but only 210 had
explicit marker assertions; 114 legacy rows had null marker fields. Astra's
separate 114-row marker replay passed. Neither that supplement nor the next probe
retroactively adds assertions to the old root receipt. The next probe explicitly
asserts markers for every designated positive, including all 19 legacy texts and
eight added ordinary inputs, for 97 IDs / 582 boundary executions. This strengthens
the external harness without dropping an input, positive check or privacy rule.

## Development outcomes and limits

The initial source repair removed sentinels from all four seats' saved HTTP input
sets. Its first context run nevertheless failed after 2,806 passes: applying the
new fallback guard to valid YAML rejected a supported block scalar containing a
static credential assignment. The guard was moved into the malformed-document
path; ordinary assignment RHS text retains its separate validation semantics.
All 2,815 existing context tests then passed. With the first 21 added formats,
3,067 context tests and 756 targeted boundary tests passed. Expanded placement
coverage adds the twenty-second format; the final context/CLI/deadline/verifier
batch passed 3,142 tests. Development results do not replace frozen-head proof.

All developmental XML/logs and failed invocations remain external. Root initially
transcribed an incomplete expected Astra report hash; that digest assertion failed
before product checks. The complete claimed and observed hashes match. Guessed
tool paths and truncated displays were not reported as verification passes.
The failed correctness seat's 16-case regression run (8 failures / 8 passes),
initial collection error, diagnostic HTTP FAIL and other partial results retain
their actual outcomes. A saved report is not a completed review or usable vote.

The old candidate's 11,725 full tests, native 11,227/322 per platform, nine distinct
CI checks and 13,062 HTTP executions remain valid only for their tested source and
inputs. They do not cover the new counterexamples. The native macOS 325.022-second
collection exceeds the 300-second proof-cost target and remains flagged; it meets
the unchanged 600-second collection limit. The configured full suite's duration
and five-second product deadline are different measurements. No waiver is implied.

The successor requires fresh exact-head full, native and actual HTTP execution,
then four fresh usable AGREE reviews, then a separate tools-enabled Opus 5.5 ruling
on unchanged verified source. The round-5 presidential BLOCK_MERGE remains binding.
Owner authorization past the former cap waived no invariant. No admin/force merge,
deployment, promotion, real provider/study/grant/holdout activity or empirical
acceptance follows. Unrelated dirty main/companion/study worktrees remain preserved.
