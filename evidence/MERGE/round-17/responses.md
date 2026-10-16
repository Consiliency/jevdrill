# Round-17 combined response — Consiliency/jevdrill#1

All four round-16 tasks completed on frozen `9470c408e139ffd2dbcca7fb182d4b0580dad97d`
before this repair. Correctness voted AGREE; Astra, alternative and Grok voted
DISAGREE. Task status reports no pending child runs. Root verified all 835 source
hashes and clean worktree/index after recovering the interrupted session. Complete
reports are preserved byte-for-byte in `evidence/MERGE/round-16/`; their votes do
not carry to this source. The old separate presidential BLOCK_MERGE remains binding.

## Combined repair

A16-1 / GR16-1: single-line YAML doubled apostrophes now receive the decoded
validation already applied to multiline members. Original quoted fragments are
checked before YAML can split a mixed encoded record into separate key/value
nodes. Recognized incomplete computations still reject. Static analysis never
executes supplied expressions; `str` retains its one-constant-string restriction.

ALT-R16-1: an original multiline plain scalar is validated as a complete enclosed
member using the recognized physical-line/whitespace view. LS/PS continuations
cannot shed their record context and become independently accepted expressions.

ALT-R16-2: the original sequence member, including its indented continuation, is
validated together before YAML token fallback. Adjacent credential fragments
cannot be accepted merely because individual scalar tokens look public.

GR16-2: explicit-key fallback includes same-line members, so VT-class whitespace
does not prevent computed-key validation when YAML cannot parse that source.

Expanded controls exposed JSON-log variants whose complete quoted record was
split by YAML before decoding. Escaped JSON strings containing recognized
physical lines now undergo decoded validation before that split. Normal
structural redaction still handles supported credential values; this validation
does not evaluate code or modify retained ordinary source.

## Preservation and development evidence

The matrix appends 36 formats: 318 formats times six labels, 1,908 exact strings.
All previous 282/1,692, 256/1,536, 233/1,398, 211/1,266, 191/1,146 and 173/1,038
strings and their actual rejection permissions, labels and scheme folds remain
unchanged. New formats cover the four findings in plain, JSON and log forms.

All 1,174 prior reviewer IDs remain exact. Imports add all saved actual round-16
HTTP inputs: correctness 86, Astra 52, alternative 23 and Grok 15, for 1,350
reviewer IDs. Only newly imported synthetic sentinel spellings are normalized;
source paths and hashes remain recorded. Direct replay passes 3,375 IDs /2,709
distinct texts and 216 designated positive markers. This is direct evidence,
not a new HTTP execution claim.

New ordinary tests check 17 exact-source public presentations and retain rejection
of 13 presentations already unsupported on the preceding head. The initial new
test wrongly assumed all 30 were supported; root compared baseline and modified
behavior before recording the actual contract. No preexisting positive assertion,
input or rejection permission was pruned. New accepted cases join HTTP positives.

Development failures remain failures: the first context batch had 50 failures
and 3,637 passes, the second four failures and 3,683 passes. The next two passed
3,687 each. An initial complete replay retained two JSON-log disclosures before
the decoded-fragment repair. The expanded batch had 16 failures /4,133 passes:
three sensitive log witnesses and the thirteen unsupported test assumptions.
The corrected context/CLI batch passed 4,170 tests. New six-boundary matrix tests
passed 1,296 with 10,576 deselected. Lint and formatting pass. An initial mypy
failure from reusing a local variable name was corrected; successor typing passes.
One external preparation invocation lacked PYTHONPATH and failed; the corrected
invocation explicitly includes the repository. Logs/XML and complete replay rows
are retained under `/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round17-20261016/`
and the adjacent `jevdrill-r17-*` files.

Round-16 dissenters' independently observed disclosures retain their separate
execution scopes. Astra's 312-execution and alternative's 138-execution probes
failed their privacy assertions; later positive assertions were not reached and
were independently checked by those seats. Grok's 90-execution diagnostic exit 0
means completion, not privacy success. Correctness's clean corpus does not negate
those counterexamples. Reported reading/path/audit limitations remain in the
complete reports and are not upgraded into proof.

## Remaining gates

Earlier 15,154 full tests, 17,796 HTTP checks and native proof remain scoped to
`9470c408`. This successor requires new frozen-head actual HTTP, configured full
suite and native proof, four fresh usable AGREE reviews, then a separate
tools-enabled Opus 5.5 presidential ruling. No old vote carries; no invariant,
assertion, deadline, target flag or limit is waived. The native 300-second target,
600-second limit, product five-second deadline and aggregate proof durations
remain distinct. Owner continuation beyond the former cap grants no force/admin
merge or empirical acceptance. Explicit historical suggestions remain excluded.

Stopped study, disabled real preview, actual grants, private holdouts and unrelated
dirty worktrees remain preserved. No real provider, study, deployment, promotion
or adoption activity occurs in this repair or synthetic verification.
