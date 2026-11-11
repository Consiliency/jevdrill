# Round-18 combined response

This repair starts from a903353bcb394779fb528a6ac9fa61717664dfed after every
round-17 task became terminal. Complete available reports and terminal records
are preserved under evidence/MERGE/round-17. The cancelled Grok task supplies
partial diagnostics, not a usable vote. Its two reproducible findings are fixed
alongside C17-1; no peer was cancelled on dissent.

C17-1: complete decoded multiline JSON string fragments now contribute their
sanitized result to the eventual output. A successful redaction is no longer
discarded before YAML can split the original source and restore unsafe bytes.
Ordinary unchanged fragments retain their original spelling.

GR17-A: quoted multiline members are also checked using YAML's original
backslash-newline decoding before the line-preserving validation view. A joined
credential label rejects before dispatch or retention. Existing supported pure
YAML sanitization and public continuations remain covered.

GR17-B: explicit keys take precedence over generic mapping-value fallback.
The explicit key's same-line key/value spans are validated before enclosing the
multiline member. The assignment scanner likewise recognizes the key span before
a same-line colon. Static parsing does not execute supplied code.

The matrix appends 16 formats (334 formats, 2,004 strings), including all nine
C17-1 variants, three continuation presentations and four explicit-key forms.
The previous 318 formats, exact generated strings, actual rejection permissions,
labels and scheme folds are checked unchanged. Thirteen new exact-source public
controls supplement the existing positives. All six supplied-context boundaries
remain covered without weakening prior assertions.

Development evidence: the first context run failed four supported JSON value
cases (4,146 passed). Changing rejection to propagation preserved that supported
path; the next run passed 4,150. Expanded context tests passed 4,342, and with new
public controls and CLI tests 4,374 passed. New six-boundary tests passed 576
(11,872 deselected). Saved direct replay initially exposed one public LS-control
regression from validating every mapping value as an unenclosed expression.
Restricting that added validation to explicit keys fixed it. The rerun passed
3,575 input IDs and 236 positive expectations, preserving all 3,375 previous
IDs exactly. New actual reviewer inputs are imported from original saved files
with hashes; only their synthetic sentinel spelling is normalized. Grok's one
explicitly out-of-scope noncontiguous-label suggestion is retained separately,
not promoted to a blocker or claimed as covered.

The saved correctness diagnostic corpus was also replayed directly: all 4,032
inputs completed within the existing per-input one-second bound with zero
sentinel disclosures. This is separate from the six-boundary HTTP proof.

Logs, preparation code, input origins and receipts are under
/home/viperjuice/tmp/jevdrill-round18. Earlier failures remain intact, including
round-17 disk exhaustion, restart interruption and subsequent successful retry.
These development results are not a new frozen full-suite/native/HTTP proof.
Fresh exact-head proof and full independent reviews remain necessary, followed
by the separate presidential ruling. No merge, study restart, deployment,
promotion, private-data access or changes to actual grants are authorized here.

The default staged whole-diff whitespace check flags five Markdown hard-break
lines (trailing spaces) in the verbatim round-17 alternative report, lines 3–7.
They remain unchanged to preserve the report hash. The earlier round-16 blank
EOF warning also remains in full-PR history. This is not a clean whole-diff
whitespace result; the implementation, tests and new response pass their
separate whitespace check.

Final combined context, CLI, route integration and discovery privacy execution
passed all 16,822 tests with zero failures, errors or skips (168.83 seconds).
JUnit was parsed independently. Lint, format, typing, vocabulary and import
boundary checks passed. Full-suite, actual HTTP and native proof remain pending.
