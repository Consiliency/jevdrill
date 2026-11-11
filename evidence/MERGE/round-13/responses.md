# Round-13 combined response — Consiliency/jevdrill#1

All four round-12 tasks completed with DISAGREE on
`b2b49960cf7fd8c130678ac47fb76ff8e43bdcf9`, manifest SHA256
`eabcd49101f807d673a977bc307c15607465f14c5fa88a285548a279c2290b73`
(813 files). Their complete reports are preserved unchanged in
`evidence/MERGE/round-12/{correctness,alternative,astra,grok}.md`.
Root waited for the final correctness result before editing the source.
No historical vote carries forward. The separate round-5 presidential
BLOCK_MERGE remains binding until four fresh usable AGREE reviews and a new
separate presidential approval on the unchanged verified successor.

## Findings and combined repair

1. **Correctness C12-C1: quoted multiline YAML.** YAML folded physical record
   boundaries before validating scalar content, then returned the original bytes.
   Six variants disclosed on all six boundaries (36 wire / 30 raw observations);
   a second fresh execution reproduced two variants (12 wire / 10 raw).
   Original quoted scalar text is now validated before folding. Line-start
   quoted records are also inspected independently of whole-document YAML
   parsing, including single-quoted records after ordinary prose. Unsupported
   computed members reject before effects. Ordinary multiline quoted text and
   Content-Type records retain their exact-text controls.

2. **Alternative ALT-R12-1/2: mixed sequences and folded plain scalars.**
   Five sequence forms produced 30 wire / 25 raw observations; four folded scalar
   forms produced 24 wire / 20 raw observations. Sequence spans now validate their
   scanned scalar members, including folded values and unresolved expressions,
   before relying on whole-document composition. The scanner checks the shared
   deadline and the existing 10,000-node budget. Fallback scalar references retain
   their complete indented continuation before computed-member validation. The
   `:` versus `=` distinction remains: ordinary call-valued assignment RHS text
   keeps its previous preservation behavior.

3. **Astra: spaced and parenthesized keyword records.** Nineteen variants
   produced 114 wire / 95 raw observations. Callable extraction now handles spaces
   and tabs. Independently discovered parenthesized keyword associations can be
   parsed with a synthetic callable prefix without executing supplied code.
   AST source slices use that exact parsed source, preserving column offsets for
   adjacent literal checks. Existing scan/parse work bounds and the shared
   deadline remain in force. Ordinary spaced/parenthesized Content-Type keyword
   records retain their exact-text controls.

4. **Grok: invalid computed assignment targets.** Two HTTP cases produced
   12 wire / 10 raw observations. Invalid Store targets were skipped when no
   individual string token spelled the credential label. These target spans and
   independently found expression suffixes are now parsed as expressions, never
   executed. Sensitive resolved labels and unsupported computed targets reject.
   Parentheses, prose, walrus and format-call variants are covered. Valid static
   targets, MIME call-valued RHS, signed values, public revision identifiers and
   ordinary following lines retain their controls.

These are independent reviewer execution counts, not deduplicated totals.
The Grok report explicitly limits its reading of nested historical narratives;
its actual counterexample was independently corroborated by root. That reading
limitation is retained, not converted into a fully compliant approval. A fresh
successor review must satisfy the complete packet-reading requirement.

## Regression preservation and scope

The previous 191 formats, all 1,146 exact label strings and all prior rejection
permissions remain unchanged. Twenty appended formats bring the matrix to 211
formats / 1,266 strings, exercised through the existing six application boundaries.
Seven ordinary exact-text controls cover quoted lines, spaced and parenthesized
keyword records, mixed sequences and folded public text. No old fixture,
assertion, node limit, routing deadline or native acceptance limit was relaxed.

Root replayed 840 saved reviewer IDs: all previous 680 plus 160 round-12 inputs,
with zero disclosures and all 35 added positive markers preserved. The external
source manifest records the exact source hashes and exclusions. Correctness's
two explicitly supplemental observations (separately commented multiline code
and a nested encoded cousin association), Grok's five prior suggestions and two
comment-only cousin associations remain nonblocking suggestions. Their complete
inputs and measured outcomes remain in the reports and external artifacts; they
are explicitly excluded from claimed passing HTTP coverage. No new policy is
inferred from those suggestions.

## Development evidence and honest failures

Two initial context runs failed after 2,402 passes because a synthetic callable
prefix changed AST column offsets while a literal tokenizer still sliced the
unprefixed source. Both failures remain external. Correcting the source binding
then passed all 2,575 existing context tests. The first expanded run failed after
2,473 passes: a single-quoted multiline record following prose escaped the
whole-document scanner. The independent quoted-record inspection repaired that
case; the unchanged expanded matrix then passed all 2,815 context tests.
The targeted six-boundary run passed 758 tests (7,262 deselected), and CLI/deadline
and ROUTE-verifier controls passed 63 tests. These are development results, not
frozen-head full/native/actual-HTTP acceptance.

All earlier failures retain their original outcomes in the round-12 response,
complete reviewer reports and external source-bound evidence. In particular,
d4cf native/offline failures and interrupted commands, bcf's ordinary MIME
rejection, b2's first external probe assertion failure and corrected fresh
execution, the prior provider failure without a verdict, and timeout controls
that passed unchanged narrow reruns are not relabeled as passes. The 300-second
proof-cost target remains distinct from the 600-second native collection limit
and the five-second product deadline; actual native flags must be reported.

The successor requires fresh exact-head full, native and actual HTTP evidence
before board delegation. Four fresh usable AGREE reviews precede a separate
tools-enabled Opus 5.5 president; no owner waiver, admin merge or force operation
is authorized. Synthetic software verification conveys no empirical acceptance,
study/adoption permission, grant authority or deployment authorization. Unrelated
dirty main/companion/study worktrees remain untouched.
