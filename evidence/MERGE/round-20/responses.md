# Round 20 consolidated response

Base: `203222d75d8b435c7bc372386cbdfcc07d8f873c`. All round-19 seats were terminal before any implementation change. Full reports, terminal records and the alternative report's parent audit are preserved verbatim under `evidence/MERGE/round-19/`.

Round 19 outcomes: correctness availability backfill DISAGREE C19-1/C19-2; Grok DISAGREE G19-1/G19-2; Astra redteam AGREE; alternative reported AGREE but was not accepted as a usable gate vote because of factual errors and substituted/omitted original-objection dispositions. Grok explicitly disclosed incomplete original narrative reading; its actual reproductions remain actionable, not a full-PR approval. Requested Opus correctness failed with a rate limit/no vote; availability-only backfill did not replace the required president. No old vote carries. No cancel-on-dissent or safety-flag evasion occurred.

## Consolidated repair

The disclosures shared a selection defect: explicit keys were recognized only in certain line-start or braced placements, and computed-key fallback lost the original marker across Unicode line normalization.

A shared explicit-key validator now tokenizes the recognized physical-line validation view and selects complete key expressions after an actual question-mark token, outside quoted strings. It tracks delimiter depth through braced mappings and sequence members, so a colon terminates the original key at the correct depth even after prose. Both tokenizer representations of question-mark punctuation are recognized. The original key substring is retained using source offsets in the validation view; public output continues to use the original text.

Computed keys are inspected with the existing constant-string AST helper. Credential-bearing additions and unresolved call/addition keys reject before effects, including glued dollar/at prefixes and complete flow records. The rule does not execute expressions or expand supported `str` signatures. Exact quoted YAML scalars use the existing quoted-member validation, preserving public doubled-quote/multiline forms. The former `$str`/embedded-brace special-case fallback is removed in favor of the shared validation.

- C19-1: complete flow-mapping additions and flow-sequence calls are selected and rejected, including whole documents and prose wrappers.
- C19-2: LF/CR/CRLF/NEL/LS/PS validation retains the explicit-key context before logical expression selection.
- G19-1: same-line prose and glued explicit-key placements are inspected by the same rule.
- G19-2: unresolved dollar/at additions reject in standalone, bracketed and encoded contexts.

Original enclosing-record sensitivity, C18-1 sibling masking, C17-1 decoded-result propagation, public MIME/text preservation, deadlines, node/work bounds and non-execution remain required. No scope exclusion or historical failure is waived.

## Verification and failures

External evidence root: `/mnt/workspace/users/viperjuice/tmp/jevdrill-round20/`.

The first implementation run failed 40 cases (4,735 passed): this Python tokenizer emits `?` as OP, not only ERRORTOKEN. Recognizing both exposed one remaining public doubled-quote YAML regression (4,774 passed). The expanded matrix retained that same failure (5,278 passed). Preserving the exact original key slice and using existing quoted-scalar validation then passed all 5,279 context/privacy cases. All failed logs remain failures. A lint check requested itertools.pairwise instead of zip over adjacent tokens; that was corrected. Final scoped lint/format/types/vocabulary/import checks passed.

The matrix adds 42 formats across six labels: 409 formats, 2,454 strings. All previous 367 formats, exact strings, label/scheme folds, rejection permissions and placement sets remain unchanged. Thirty-six new public controls require exact original source preservation across plain, JSON and object presentations.

The new six-boundary/privacy/public selection passed 2,052 tests (18,414 deselected, 9.59 seconds). JUnit is retained externally. Direct saved-corpus replay passed all 4,337 IDs with 302 positive controls and no disclosed sentinel or missing marker. All 3,813 prior IDs remain exact; original reviewer HTTP inputs plus correctness's 150 direct inputs and 60 placement observations are imported with provenance hashes and only documented synthetic sentinel substitution. This direct result is not an HTTP execution claim. Suggestions from the reports remain explicitly outside passing coverage claims.

Fresh full-suite, actual HTTP and native proof must bind to the next frozen commit. Expected HTTP coverage is 26,022 executions and 1,812 literal-true positive rows. These are expectations, not completed results. The prior 19,301 full tests, 22,878 HTTP executions and nine successful CI checks remain historical. Prior round-18 full-run failures retain unconfirmed causes; no new cause is inferred. Native 300-second target flags, 600-second collection limit, full-suite duration and five-second product deadline remain distinct and unchanged.

The old proof inventory included mutable continuation.json/pr-body.md summaries; both review audits explicitly identified their later mismatches. The original proof inventory is preserved. New proof must distinguish immutable inputs/results from mutable coordination and bind final summaries separately before presidential reliance.

Verbatim historical report whitespace is preserved; no whole-diff whitespace-clean claim. Original F6/F7/D2/D4/D6/Q-12/Q-13 and empirical study concerns remain unresolved. Stopped study, disabled preview, private data, grants and unrelated dirty worktrees are untouched. No real provider or study authority, deployment, promotion, adoption or empirical acceptance follows from software checks.

Merge still requires exact-head proof, four fresh usable full-PR AGREE reviews, then a new separate tools-enabled Opus 5.5 presidential ruling. Old round-5 BLOCK_MERGE remains binding. No force/admin merge or invariant waiver is authorized.
