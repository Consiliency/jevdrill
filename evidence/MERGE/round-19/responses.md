# Round 19 consolidated response

Base: `846770a3a10babac4fe6692257e862eae64d3b3b`. All round-18 seats reached terminal states before source changes. Full reports and terminal records are preserved in `evidence/MERGE/round-18/`.

Correctness availability backfill DISAGREE C18-1; Grok DISAGREE G18-1 through G18-4; Astra red-team AGREE; alternative reported AGREE with original-report reading/disposition coverage audit still outstanding. The requested Opus correctness run failed with a rate limit and supplies no vote. No vote carries to this candidate. No safety-flag retry or substitution occurred. The old presidential BLOCK_MERGE remains binding; four fresh usable full-PR AGREE reviews and a new separate tools-enabled Opus 5.5 president remain required.

## Changes

- C18-1: decoded strings are validated without rewriting the original enclosing record. Mapping/sequence sensitivity is decided from original labels before recursive member sanitization. Changed decoded spans must correspond to complete scalar spans, and a structured result cannot return unchanged after such a decoded change. Unstructured prose reaches the existing complete JSON-fragment decoder, which propagates sanitized fragments. This preserves the C17-1 requirement instead of discarding a cleaned result or restoring unchecked original bytes.
- G18-1: explicit-key recognition permits a glued `?` and validates the key separately from its sibling value.
- G18-2: complete JSON strings are validated even without escapes or physical line breaks, including recursively encoded prose wrappers.
- G18-3: bracketed explicit flow records inside prose receive the same handling as standalone records; unsupported dollar-prefixed computed explicit keys reject before effects.
- G18-4: inline backtick member validation also runs on the top-level assignment path.

No supplied expression is executed. The literal `str` helper, limits, product deadline, prior input strings, labels, scheme folds, assertions, and rejection permissions are unchanged. No scope exclusion is converted into a claimed fix.

The matrix adds 33 formats (original object/key/array/header association and seven placement forms, plus JSON/object wrappers): 367 formats by six labels, 2,202 strings. Twenty-four public controls require exact original source preservation. External saved-corpus preparation preserves all 3,575 preceding IDs exactly and imports both reviewers' actual HTTP inputs, changing only synthetic sentinel spellings with original hashes retained. The expanded corpus has 3,813 IDs and 262 positive controls. Direct replay passed with no disclosures or missing positive markers; this is not HTTP proof.

## Development evidence and remaining gates

External evidence: `/mnt/workspace/users/viperjuice/tmp/jevdrill-round19/`.

The first development context/privacy run failed 23 cases (4,332 passed): nested-string over-rejection and public explicit-key over-rejection. The narrowed checks then passed 4,355 cases. Expanded tests exposed 14 prose-prefixed original-record sibling disclosures (4,737 passed), showing why fragment rewriting had to be deferred until enclosing-record handling. Removing that rewrite passed 4,751 cases; adding explicit span/changed-result checks again passed 4,751. With public controls, 4,774 privacy tests passed. Original failed logs remain preserved and are not passes.

An overly broad `ruff check .` / `ruff format --check .` invocation included unrelated legacy catalog scripts/tests and failed (format: 43 files). No unrelated files were reformatted. The first mypy invocation found a new string/bytes local-name collision in the embedded fragment check; this is corrected before final verification. Vocabulary and import-boundary checks passed. Final scoped static checks and combined-boundary results are recorded separately below.

Full-suite, actual HTTP, and native CI proof must bind to the new frozen commit. Round-18's 17,693-test full pass, 21,450 HTTP executions, and nine passing checks remain historical; they do not prove this candidate. Round-18's interrupted first full attempt and failed retry 1 still have unconfirmed causes. The three native 300-second target flags remain visible and distinct from the 600-second limit and five-second product deadline. Verbatim historical report whitespace is preserved.

No empirical study acceptance, real provider/private data/grant/holdout authority, deployment, promotion, or adoption is granted. Stopped study and preview remain untouched. F6/F7, D2/D4/D6, Q-12/Q-13 and all original unresolved study concerns remain retained.

Final scoped lint/format/types/vocabulary/import checks passed. Combined context/privacy, route integration, discovery, and CLI selection passed 9,368 tests (68.51 seconds); new composed privacy selection passed 1,212 tests with 12,648 deselected (12.02 seconds). Both JUnit files contain zero failures/errors/skips. The combined selection includes 396 new composed route tests. These selected runs and direct replay are development evidence, not the full-suite or actual HTTP gate.
