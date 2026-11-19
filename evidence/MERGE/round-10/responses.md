# Round 10 combined repair response

Previous candidate: `b8e6ce61480e86d85645b28f711313d006582293`.
All four round-9 seats completed before any source or tracked-evidence edits.
Correctness, Astra, alternative and Grok all voted **DISAGREE**. Their complete
reports are preserved in `evidence/MERGE/round-9/{correctness,astra,alternative,grok}.md`.
No approval carries forward, and the separate round-5 presidential BLOCK_MERGE
remains binding. The owner authorized continuation beyond the former cap, not
waivers of privacy or execution bounds.

## Verified previous candidate and missing coverage

That candidate passed all **3,863 configured tests**, zero failures/errors/skips,
in 466.718 seconds with clean unchanged HEAD and all 796 tracked hashes. JUnit
SHA256: `9d6ac37932a33beb9a6d6d43d4327be66a048e47e1ce4f27b324d31374b6b806`.
Its complete 2,082-check actual HTTP receipt passed its tested inputs; SHA256:
`e3dc4e241b6666222b772e8705440efff52d254d6c5bac3958d562143e764675`.
All nine distinct CI checks and 14 actual check instances passed. Real native
ROUTE/CONTRACT manifests reduced locally against current digests with zero errors.
ROUTE passed 3,365 tests per platform; CONTRACT passed 322 per platform. Windows
completed collection in 156.579 seconds with cold CLI at 0.623 seconds using runner
temp. These receipts remain valid for that execution; they omitted the newly
demonstrated combinations and do not close the reviewers' findings.

Historical Windows failures, root's omitted-dash disclosure and the case-ID
collision in an earlier partial probe retain their original scope and status.
The current passing attempt supports the runner-temp placement change without
fabricating causes for all earlier failures.

## Combined objections and repairs

1. **Physical line boundaries in mixed records (M2).** Correctness reproduced
   three CR forms through six boundaries: 18 HTTP and 15 raw-artifact disclosures.
   Alternative crossed three forms with all six labels/boundaries: 108 HTTP and
   90 raw-artifact disclosures. Astra also reproduced CR block labels and mixed
   sequences separated by NEL, Unicode line separator and paragraph separator.
   The original-source guards and fallback field scan now share explicit physical
   line-start, line-content, indentation and continuation definitions covering
   CR, LF, CRLF, NEL, LS and PS. Original input bytes remain available for structural
   parsing and supported Python assignment offsets; the source is not globally
   rewritten to manufacture associations.
2. **Dash-only sequence items (M2).** Grok reproduced a mixed space-indented item
   and an unparseable tab-indented item: 12 submissions and ten raw artifacts.
   The original-source sequence scan now accepts a dash followed by a line end as
   well as same-line whitespace/content, and includes following indented lines.
   Credential-bearing mixed/unparseable sequences reject before effects. Separate
   pure-YAML controls require successful sanitization rather than accepting a
   blanket rejection of valid whole sequences.
3. **Formatted and computed literal labels (M2).** Correctness reproduced three
   expression-free f-string record forms: 18 submissions and 15 raw artifacts;
   Grok independently reproduced a plain/f-string mixture. Astra demonstrated
   three constant-addition assignment targets: 18 submissions and 15 raw artifacts.
   A bounded AST-only string interpreter handles string/bytes constants, constant
   addition and expression-free formatted fragments. The unified label predicate
   uses the decoded result, and assignment target inspection checks composed
   values. Complete logical literal records receive the same computed-string
   inspection before fragment handling. No supplied expression executes.
   Unsupported computed literal records reject; known sensitive single-line
   assignment targets still mask the whole value, including call expressions,
   and preserve ordinary following text. Noncredential constant Content-Type
   additions/formatted fragments remain usable.
4. **Standalone Basic/Bearer folds (M2).** Astra reproduced 72 HTTP and 60 raw
   disclosures across its folded-scheme inputs/boundaries. The standalone-scheme
   alternative now consumes the complete recognized value and its indented
   continuations using the common physical-line rules. Whitespace-only continuation
   lines and leading indentation are included. Ordinary unindented following text
   has explicit positive controls and is retained.
5. **Private-key scan cost (M1/M3).** Alternative measured 0.286/1.086/4.051 CPU
   seconds for 1,000/2,000/4,000 incomplete openers. A valid 147,656-byte CLI request
   with judgments disabled exceeded five seconds, returning at 6.765 seconds.
   The overlapping-suffix private-key regex was removed from the credential and
   fragment alternatives. Delimiters are scanned in order; a missing closer rejects
   promptly, and openers inside an already covered span are skipped. Deadline
   checks remain in the scan. Complete blocks are validated before structural
   parsing but are not destructively rewritten before original label associations
   are inspected. Actual removal occurs during plain-value sanitization. A YAML
   block containing a credential label and sibling payload has a positive control
   against repeating the earlier destructive-rewriting defect.

The five numbered groups include six concrete blocker families: physical line
boundaries, dash-only items, formatted-string labels, constant-expression targets,
standalone folds and private-key scan complexity. Counts from independent seats
overlap; they are not summed into a misleading unique-disclosure total. Full
per-seat receipts and limits remain in the preserved reports.

## Coverage and development verification

All 53 previous generated formats, all six labels and all 318 format/label inputs
remain byte-identical. Their previous permitted-rejection classifications remain
unchanged. The matrix adds computed labels and mixed records across all supported
physical line boundaries, with six actual submission/retention boundaries retained.
Standalone scheme cases are separate from label-dependent formats. Valid whole
dash-only YAML, ordinary following text, noncredential computed labels and complete
private-key blocks retain positive controls.

The initial repair passed 5,117 focused tests. Root's additional direct probes then
found three related surviving forms: replacement-field f-strings, call-computed
targets and call-computed record labels. These are not passing privacy evidence.
Their handling is now explicitly fail-closed within the bounded literal grammar,
and the generated matrix includes all three across every label. A development run
initially rejected five supported sensitive assignments with call-valued right-hand
sides and missed an expression with no literal fragments; six unit failures were
preserved. Deferring the unresolved-record rejection until after complete sensitive
target masking and recognizing unresolved formatted records corrected both paths.
The subsequent unit/CLI run passed **1,402 tests**, zero failures/errors/skips.
Changed-file Ruff checks/formatting and strict mypy over all 23 source modules pass.

For 1,000/2,000/4,000/5,000 incomplete private-key openers, local repaired direct
redaction rejected in approximately 0.032/0.036/0.066/0.075 milliseconds of CPU.
These are local processing measurements, not native acceptance. The new actual CLI
regression must still satisfy the unchanged five-second assertion and return one
invalid-input JSON response with empty stderr. Neither the six-second parent
process guard nor the 600-second native collector budget changed.

Final combined focused verification, clean exact-head configured verification,
complete actual HTTP verification, current native CI, four fresh AGREE votes and
the separate presidential ruling remain required. No real provider, study, grant,
holdout, deployment, policy promotion or adoption activity is authorized or claimed.
The disabled/expired real preview, stopped study, real grants, dirty composer and
companion worktrees remain preserved. Synthetic loopbacks use separate authority.

The final combined focused run passed **5,262 tests**, zero failures/errors/skips,
in 65.04 seconds, after the computed-record corrections. There are now **95 generated
formats** and **24 standalone-scheme cases**. This is development-tree verification;
clean exact-head full/native/HTTP results and approvals remain pending.
