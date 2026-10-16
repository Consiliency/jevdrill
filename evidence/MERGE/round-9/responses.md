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

## CI aggregation follow-up

Candidate `2cd84c1bbf39791d8c61080c546b2f6a0d6d7e46` passed all **3,803 configured
tests**, zero failures/errors/skips, in 439.690 seconds, with its clean HEAD and
all 796 tracked hashes unchanged. JUnit SHA256:
`8f14b8dfa5c2bcbe8e5676a0f60aa5e6efabfef98ebfa269abd1420ddcac6431`.
Its actual DevelopmentJudge loopback passed **1,962 executions**, 918 local HTTP
requests and 1,044 pre-dispatch rejections, with zero disclosures. Receipt SHA256:
`4f86b1d1293335ced4d586540d47f29b57fb5f8b02825f5cd0d0d04661effce4`.

The first Windows attempt failed three CLI controls (two storage_failure responses
and one six-second subprocess timeout), while 3,302 tests and all later checks
passed. Its logs/manifest were preserved. One unchanged-head retry passed all
3,305 selected tests. The first attempt's cause remains unestablished; it is not
retroactively a pass. No timeout or assertion changed.

The subsequent reducer failed because `route-*` also downloaded the previous
`route-verification` summary into the platform directory. Independent reduction of
the three latest native manifests on the unchanged candidate produces **zero errors**;
adding the summary produces exactly `malformed platform identity`. Linux/Darwin/
Windows each passed 3,305 tests, with collection durations 150.988/136.832/394.043s.

Native artifact names and selectors now use a separate `*-native-*` namespace in
ROUTE, CONTRACT, HOST and LEARN, excluding their aggregate summaries on retries.
A four-workflow regression selects the declared three native producers in the
presence of an earlier aggregate report. Reducer identity/source/check validation
is unchanged. Runtime files and credential fixtures remain byte-identical to
`2cd84c1bb`; fresh exact-head verification and review are still required for this
workflow-only follow-up.

## Windows timeout diagnostics

Candidate `f4439a666025358a58daa8031b4cbfee5c4b2840` passed all **3,807 configured
tests**, zero failures/errors/skips, in 442.928 seconds with unchanged clean HEAD
and all tracked hashes. JUnit SHA256:
`d55dd4feaf6ee3e93b08a2acd84b55db06fa7cbbf2e6f476e1a59c9ef4ff5be6`.
Its Windows collector nevertheless exhausted the unchanged 600-second budget
(600.254s total; first command 599.868s) and produced no completed JUnit report.
The zero test count in that failed manifest does not prove that no tests ran.
The collector discarded TimeoutExpired's partial stdout/stderr, so the last test
and underlying cause cannot be established from that attempt. Its log and manifest
are preserved externally; no failure is waived or claimed fixed.

This diagnostic-only follow-up retains captured timeout stdout/stderr, including
their bytes in the output digest while retaining exit code 125. The selected
pytest command emits node names and requests a faulthandler stack dump after a
test stalls for 30 seconds. Selected paths/assertions, the 600-second collector
limit and five-second CLI limit are unchanged. A synthetic collector regression
checks that both streams reach the failure log/hash and that a timeout remains a
failed check with no fabricated completed test count. The 30-second timer only
dumps diagnostics; it does not terminate or grant time to a test.

Runtime files remain byte-identical to `2cd84c1bb`. Fresh exact-head configured
verification and Windows collection are required; diagnostic evidence is not
native acceptance and the timeout's cause remains open.

## Plain-text deadline repair

Candidate `0538011c64f3a37137e6e518529a049c9e6f0408` passed all **3,808 configured
tests**, zero failures/errors/skips, in 522.937 seconds with unchanged clean HEAD
and tracked hashes. JUnit SHA256:
`db60daab0c1e5c35fcb858a8299ac6994deaa89758cc295fd6cfe55fa5aec662`.
Windows completed 3,310 native tests in this attempt (446.426s total collection),
but the two continuation CLI regressions exceeded five seconds: 5.116s for 2,000
ordinary continuations and 5.166s for 20,000 short continuations. The other 3,308
tests and every subsequent check passed. This establishes specific failing inputs,
not the causes of earlier unrelated CLI failures or the prior whole-suite timeout.

Local profiling identifies avoidable YAML scanning/composition and Python
tokenization for these inputs. Text without structural punctuation cannot contain
the supported mappings, literal strings, assignments, graph/tag/comment or block
forms. It now uses the existing plain-text credential redactor directly; inputs
with any such punctuation still follow the complete structural pipeline. Bare
Basic/Bearer credentials and private-key blocks remain subject to plain redaction.

Measured local redaction for the 2,000/20,000-line inputs decreased from about
23.7/98.1ms to median 2.37/7.84ms, preserving the original text. These are local
processing measurements, not proof of the Windows failure's underlying phase.
If a CLI deadline still fails, its test prints the original return code/response
and database-presence metadata, then performs a separate CPU-profile diagnostic
rerun. The original measured invocation must still finish within five seconds;
diagnostic success cannot satisfy that assertion. A synthetic forced failure
confirmed the profile executes and the original assertion remains failed.

**2,945 focused context/privacy/route/CLI tests pass**, as do changed-file Ruff
and strict source mypy. All earlier cases/assertions remain, with three plain-text
controls for unchanged continuations, folded Basic and private-key removal.
Fresh full configured verification, actual six-boundary HTTP regressions, native
CI and all review approvals remain pending for this repair at commit time.

### Fast-path YAML sequence correction

During root's own review of `b78de2fc8aba85701b1135c85722e37d3dba5470`, the initial
fast-path guard omitted YAML's block-sequence dash. The valid input
`- Authorization\n- SYNTHETIC_SENTINEL` bypassed structural sibling masking.
An actual six-boundary DevelopmentJudge probe reproduced **six submission
disclosures and five raw-artifact disclosures**, with no database disclosures.
Receipt SHA256:
`d5cd177c2853b4a5b4a6f2906ecbf2abee1c85fdd812394ee0d640eb9ae6978f`.
The separate 1,974-case run on that head passed its tested forms but omitted this
representation; it does not close this finding. No configured full-suite pass or
approval is claimed for that candidate.

The corrected guard includes block-sequence/document/directive punctuation.
Whole YAML header-pair sequences receive normal structural sibling masking;
unparseable mixed credential sequences reject from the original source, including
indented block labels, before fragment or assignment rewriting. The generated
matrix adds unquoted YAML block pairs for every label and preserves all prior
identities/assertions. Three additional pure-YAML controls require sanitization,
so accepting a rejection cannot silently replace support for these valid pairs.

**2,996 focused context/privacy/route/CLI tests pass**, with zero failures; Ruff
and strict source mypy pass. Exact-head six-boundary HTTP checks, configured full
verification and native CI must be collected for this correction before review.

### Installed-wheel deadline diagnostics

Candidate `94b54eb01f0b6d484535a90d25067e9658fbca00` passed all **3,862 configured
tests**, zero failures/errors/skips, in 468.030 seconds with clean unchanged HEAD
and all 796 tracked hashes. JUnit SHA256:
`3d09f1b6f4ce405b7cb1ba6e7ebc1ed62ab695e38a6a2ebeb076368521129c2a`.
The complete actual HTTP probe passed **2,082 checks**, 347 distinct inputs across
six boundaries, with 966 requests, 1,116 pre-effect rejections and zero detected
disclosures. Receipt SHA256:
`4002a137f904c885b9ce688c65b4f43023df65a0ec5b8b7c06ca32560260ed58`.
An earlier 2,046-case probe had colliding mixed-YAML case IDs and is not the complete
matrix receipt; the corrected probe asserts distinct IDs/count and binds its inputs.

Windows passed the prior continuation controls but failed a discovery privacy case
at its storage deadline and the installed-wheel CLI at its five-second subprocess
limit. The separate installed-package check also failed the same CLI timeout.
The main run completed 3,364 tests (3,362 passed, two failed), and collection took
511.610 seconds. Cold CLI passed in 4.314 seconds. The reducer correctly blocked
failed checks/assertions with all three platform identities present. This is not
an artifact-selection failure, and neither failed check is waived. Their underlying
slow phase remains unestablished; local import timing is not a Windows diagnosis.

On an installed-wheel timeout or nonzero return, its test now prints the original
failure and runs a separate diagnostic child using that same installed interpreter
and dependency environment, a separate database, import timings, cumulative CPU
profile and a three-second repeating stack dump. The original command, five-second
timeout and ready-result assertion remain unchanged. The diagnostic has a separate
six-second process bound; it cannot satisfy the original assertion or turn a timeout
into a pass. No runtime file or authority changed in this diagnostic follow-up.
Fresh exact-head verification and Windows evidence remain required.

All eight selected package/continuation tests and 24 explicit escaped-target
discovery privacy cases pass locally; changed-file lint/format checks pass.
Separate synthetic timeout and nonzero-return probes each built and installed the
real wheel, forced only the original CLI failure, and confirmed the diagnostic
child emitted import timings and CPU profile while the original TimeoutExpired
or AssertionError still propagated. These probes validate failure diagnostics,
not the cause or repair of the Windows deadline failures.
