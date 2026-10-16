# Round-11 combined response — Consiliency/jevdrill#1

All four round-10 seats completed with DISAGREE on
`392f2234f397aaee0725c6b37c9ef42c15587bf7`, manifest
`d99836fab215e0d0a96f37e152d2597ee35ea394d02bf5d587bc293d86f877c2`
(801 tracked files). No source or index edits began until all four finished.
Complete reports are preserved in `evidence/MERGE/round-10/`.

Passing historical verification remains valid for its tested inputs: 6,118 full
tests, nine distinct CI checks and 14 instances, native ROUTE 5,620 and CONTRACT
322 tests per platform, and the 5,166-execution supplied HTTP matrix. Those passes
did not cover the newly demonstrated disclosures or large-sequence deadline miss.
No former AGREE carries forward. The separate round-5 Opus 5.5 BLOCK_MERGE remains
binding; owner authorization to continue beyond the former cap waived no blocker.

## Findings and repair

1. **Correctness C10-1 and Astra inline-computed-record blocker.** Prose or Markdown
   made whole-line Python parsing fail, bypassing composed-label inspection in
   mappings, pairs and assignment targets. Correctness reproduced 102 HTTP and 85
   raw-artifact disclosures; Astra's inline family reproduced 60 HTTP and 50 raw
   disclosures. Receipt hashes are in the full reports; counts are independent
   reviewer executions, not a deduplicated total. Inspection now considers
   complete bracketed fragments independently of presentation text. Parsed outer
   fragments cover their children; invalid outer fragments still permit inspection
   of complete inner records. Fragment parse work is bounded relative to input.
   Static sensitive assignments still mask complete values and preserve ordinary
   following lines. Noncredential constant and formatted Content-Type controls,
   including inline/nested wrappers, remain usable.

2. **Astra and Grok no-string-constant computed-record blockers.** Numeric `chr`
   chains, bare calls, name additions and name slices escaped the previous
   string-constant prerequisite. Astra reproduced 24 HTTP and 20 raw disclosures;
   Grok reproduced 48 HTTP and 40 raw disclosures. Unresolved computed records
   now reject independently of the presence of string constants. Subscript label
   expressions are inspected as well. Supported static labels and complete
   sensitive assignments with call-valued right-hand sides retain their controls.
   Supplied code is never executed.

3. **Alternative structured-parser bypass.** YAML accepted Python call-computed
   mappings and keys as scalar text, allowing an early structured return to bypass
   whole-record inspection (48 HTTP and 40 raw disclosures). A structured parse
   now undergoes nonmutating complete-record validation before acceptance. The
   assignment validator's rewritten output is deliberately discarded at that
   point: original YAML label/member associations remain available for sibling
   masking, preserving the earlier association-ordering repair.

4. **Alternative YAML composition deadline blocker.** Its schema-valid 802,657-byte
   request with 400,000 sequence entries exceeded the unchanged five-second CLI
   limit; a six-second parent guard expired. Separate instrumentation measured
   uninterruptible composition ending at 5.600 seconds before the deadline check.
   Scanning now rejects documents exceeding 10,000 scalar/container nodes before
   composition. The composer also checks the shared deadline at each node. An
   actual 400,000-entry CLI regression requires rejection within the original
   five seconds, with ordinary structured-context controls retained. Neither the
   product deadline nor the 600-second native collector limit was increased.

## Development verification and honest limits

The first focused run passed 2,041 tests and failed the ordinary escaped-literal
warning assertion: invoking validation on structured input exposed an unsuppressed
SyntaxWarning. That was corrected, along with two mypy annotations and an explicit
CLI-test argument placement error caught before that case ran. The next run passed
6,011 privacy/CLI checks. Root then independently reproduced a nested-wrapper
disclosure in that intermediate tree and repaired it; the broader targeted run
passed 6,288 tests (privacy, CLI, context and verifier controls), zero failures,
errors or skips, in 108.30 seconds. These are development outcomes, not clean-head
acceptance evidence.

A preservation comparison caught a new fixture name-prefix rule unintentionally
permitting rejection of six historical inline-comment inputs. The rule was narrowed
to explicit new-format membership. All 95 prior formats, six labels and 570 exact
format/label strings and prior permitted-rejection classifications are unchanged.
There are now 155 formats. Changed-file lint/format checks and strict mypy over all
23 source modules pass. The final context/privacy run after restoring those fixture
classifications passed 2,106 tests, zero failures/errors/skips, in 1.54 seconds.
Final exact-head full, actual HTTP and native evidence must
be produced after this response and the reports are committed.

The next complete HTTP matrix carries the prior 238 reviewer IDs plus all 210
round-10 correctness/Astra/alternative inputs and Grok's eight exact blocker cases:
456 reviewer IDs total, with source-file hashes retained. IDs and distinct text
counts remain separate. OpenPGP armor, colonless/unassociated text, homoglyphs,
zero-width labels, unlabeled calls and cousin associations remain nonblocking
suggestions with their historical evidence; this response does not reclassify them
as repaired blockers or silently include their disclosure cases in a claimed pass.
Earlier full reports, Windows failures/timeouts, omitted-dash disclosure,
private-key deadline miss, colliding-ID partial evidence and corrected development
failures retain their original outcomes and bindings. Correctness's missing-
companion invocation remains a failed unconfigured invocation, not a product defect.

All remaining presidential requirements, spending/model/provider authority,
replay/recovery/idempotency, deletion/retention, portable-v1 fail-closed omissions,
SDK/publication and downstream verification remain in full-PR review. No new review
approval is claimed here. Four fresh exact-head AGREE votes and a subsequent
separate explicit Opus 5.5 presidential approval are still required before normal
merge. No real study/provider/grant/holdout activity, policy promotion, deployment,
adoption or empirical acceptance is authorized or claimed. Unrelated dirty
composer/companion and stopped-study worktrees remain untouched.
