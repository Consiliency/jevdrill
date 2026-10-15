# Round 9 combined repair response

Previous candidate: `4dd336a0282bf177f41dbc4929748289fef5d68c`.
All four round-8 reviews finished before any repair. Complete reports are preserved in
`evidence/MERGE/round-8/{correctness,astra,alternative,grok}.md`.
Correctness, Astra and alternative voted DISAGREE; Grok voted AGREE. The dissenting
reproductions govern the repair. Grok's approval does not waive them or the separate
round-5 presidential BLOCK_MERGE.

## Combined blockers and repairs

1. **Adjacent Python literal labels in mappings/arrays (M2).** Logical-token
   inspection recognizes concatenated strings. Unresolved credential-bearing
   literal records reject before dispatch or retention. Complete single-line
   assignment targets still use AST interpretation and sanitize, including adjacent
   literal targets. Member-preserving structured handling remains unchanged.
2. **Implicitly continued assignment targets and bare CR boundaries (M2).**
   Assignment inspection consumes complete logical statements, normalizing CR/LF/CRLF
   only for tokenization and mapping token positions back to original bytes.
   Parenthesized, tuple, attribute and subscript targets spanning implicit lines
   reject. Explicit target continuations and complete single-line assignments remain
   supported. No supplied code is executed.
3. **Assignment rewriting erases YAML label associations (M2).** Original structured
   nodes are inspected before assignment rewriting. Credential-bearing block scalars
   mask sibling values. Unparseable mixed records with credential-bearing blocks
   reject from original source before any destructive rewrite.
4. **Quadratic explicit-continuation scan (M1/M3).** The overlapping suffix regex is
   replaced by sequential logical tokenization. Each continuation chain is consumed
   once, with deadline checks during line and token traversal. Target segments are
   parsed once per assignment separator. The five-second CLI budget is unchanged.
5. **Parser MemoryError escapes public JSON boundary (M1).** Unquoted YAML scalars
   are no longer passed to Python literal evaluation. Literal parser resource
   failures become ContractError at the sanitizer boundary. A synthetic MemoryError
   control and the actual formerly failing CLI continuation input cover both paths.

The generated matrix adds ten formats for all six existing labels: concatenated
mapping names/keys/header pairs, implicit/subscript/tuple/augmented targets, bare-CR
targets and three YAML block-assignment forms. It retains every prior case and
submission/retention assertion. Additional unit cases cover parenthesized bare and
attribute targets with both operators and all three physical line endings.
No timeout, collector command, acceptance threshold or production authority changed.

## Verification at repair preparation

- Focused context/privacy/CLI run: **2,216 passed**, zero failures/errors/skips;
  JUnit stored externally as `repair-targeted.xml` under the persistent round-8
  working directory. This includes the corrected implementation and all new matrix
  formats; it is an uncommitted-tree run, not an exact-head acceptance receipt.
- Preceding context/CLI run: **785 passed**. Earlier development runs failed on
  explicit target continuations, mixed YAML blocks and a wrong expected routing
  status; those failures prompted the corrections above and are not passes.
- Changed-file Ruff checks and strict source mypy passed. An overly broad exploratory
  Ruff run included existing top-level catalog tests outside the configured phase
  scope and reported their existing formatting/import issues; no unrelated files
  were changed. Phase-required checks must still be verified.
- Full configured suite, actual DevelopmentJudge local HTTP regressions, exact-head
  native CI, four fresh reviews and a separate presidential ruling remain pending
  at commit time. Previous-head passing receipts are not relabeled as this execution.

The real disabled/expired study preview, stopped study, dirty composer checkout and
companion worktree remain preserved. All new probes use synthetic inputs and local
HTTP only. No real provider, study, grant, holdout, deployment, promotion or adoption
is authorized or claimed.
