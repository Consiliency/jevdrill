# ROUTE readiness

The ROUTE verifier selects its phase-owned tests explicitly, including every required executed control. HOST, LEARN and EXPERIMENT collectors explicitly add their own required JEV test suites, and their reducers bind those commands and assertions. Installed companion conformance remains part of the downstream collectors and the separately configured full suite.

ROUTE implements discovery, durable task routing/reporting and replay on the
strict BAML boundary. Discovery advances its own questions through catalog
metadata, records uncertainty and returns admitted instructions. A successful
stored discovery can feed each independently constrained task through route-v2.
The application does not decompose objectives or launch executors; HOST must be
replanned against the interfaces in `docs/route-interfaces.md`.

The current verdict is `evidence/ROUTE/verification.json`. Acceptance requires
all seven EC-ROUTE criteria and IF-0-VC-2, matching current-source native
Linux/macOS/Windows Python 3.13 manifests, pinned generation, shared fixtures,
privacy/crash controls, installed-package checks and the five-second cold CLI
boundary. The reducer checks executed test identities and outcomes as well as
command, source and assertion digests. Old four-criterion reports and skipped or
missing controls fail. Earlier reports remain under `evidence/ROUTE/history/`.

```sh
BAML_CLI=/path/to/baml-cli uv run python scripts/verify_route_phase.py --local-only
uv run python scripts/verify_route_phase.py --reduce-only
```

Local-only collects one native platform and does not close the full matrix.
Collection is bounded to ten minutes; reports flag runs above the five-minute
proof-cost target. Neither allowance changes the product deadline.

The CLI accepts one JSON document on stdin and produces one JSON response on
stdout. Use `--storage PATH` and the host's spawn-inclusive
`--remaining-budget-ms N`. Commands are `discover`, `route`, `report`,
`inspect`, `delete`, `inspect-discovery` and `delete-discovery`. Exit codes are
0 handled response, 2 invalid input/version, 3 idempotency conflict and
4 infrastructure/deadline failure. Native Windows verification uses the installed
interpreter with `-m jevdrill.cli`, following the existing unsigned-launcher
configuration; it does not change security policy.

Request privacy and provider authority apply before each built-in or injected discovery adapter call.

Requests needing a new injected task or discovery judgment with an explicit spending ceiling fail before preparation or dispatch; that adapter mode is unsupported. Built-in adapters retain their verified pricing checks. The request model must match the configured adapter model, and the supported token counter is `utf8-bytes-upper-bound-v1`. DevelopmentJudge is pinned to `jev-1.13.0`; built-in and ordinary synthetic observers use `jev-latest`.

Discovery reserves provider work durably before dispatch. Each key has its own
immutable allowance; interrupted same-key recovery makes no new provider call.
It atomically commits supported partial guidance or interrupted failure.
Terminal observations are audit-only. Objective tombstones span producers in
one project/workspace and invalidate all attempts, retries, replay and linked
route commits. Existing task records keep their independent lifecycle.

Raw objective/context/description retention is opt-in. Retained discovery content uses the ordinary artifact lifecycle, keyed by its discovery ID: archive prompt, encrypted archival after the grace period, and expiry. Seeds, questions and replay traces remain metadata-only; retries do not recreate expired raw content. Objective deletion removes the associated artifacts.

Portable v1 recovery preserves successful discovery metadata but omits raw discovery artifacts, whose objective-to-content lifecycle mapping is local. Local encrypted archival and restore remain available before expiry; portable recovery does not revive deleted objective content.

Metadata replay validates
questions, answers, FIFO transitions, budget deltas and deterministic selection
from recorded admission/compatibility/context facts without regenerating prompts
or using a live catalog. Credentials and excluded attachments are sanitized
before submission/persistence. Selected catalog instructions remain local except
for explicitly returned guidance. No hidden reasoning is retained.

Supplied JSON, YAML and supported literal mappings retain member pairs during
sanitization. Credential labels use the same authorization/API-key/access-token/
password/secret rule, including prefixed labels. A labeled mapping or header-pair
array masks sibling values; encoded string layers are sanitized recursively.
Free-text credential assignments include their complete line and indented
continuations. Unsupported credential representations and excessive nesting
fail before judgment submission and raw retention.
YAML anchors, aliases, merge keys, explicit tags and non-scalar mapping keys,
ambiguous escaped or concatenated literal labels, mixed credential records that cannot be
structurally parsed, and multiline code assignments are rejected. Assignment
targets are inspected as complete logical statements, including augmented operators,
CR/LF/CRLF boundaries and literal labels; implicit multiline targets and incomplete
expressions reject. Before rewriting a decoded sensitive array fragment, local
forward inspection follows Unicode identifier attributes, balanced postfix
subscripts, annotations and continuations through the associated operator;
unresolved sensitive target ownership rejects within the existing work and deadline bounds.
Locally spelled credential names and attributes followed by subscripts,
tuple targets, or explicit continuations are checked independently of
surrounding prose tokenization. Locally parsed Python identifiers use
Python continuation rules; both raw and NFKC spellings are passed to the existing
credential-label predicate; structured labels retain their prior scope.
After existing complete-statement redaction, a bounded local parser checks surviving
Python assignment targets inside prose and quoted text. It follows runtime-valid
identifier spellings (including supported format continuations), grouping, tuples,
lists, attributes, subscripts, annotations, augmented operators, and CR/LF/CRLF
continuations; a recognized sensitive target is rejected before application effects.
Locally complete assignment expressions (`:=`) are parsed as Python expressions
within balanced containers or condition clauses; their actual `NamedExpr` targets
are checked using the raw source spelling as well as its NFKC spelling. The
statement-target parser likewise checks the raw spelling at each actual Name or
Attribute owner's source span before Python's AST normalization can erase an
ASCII credential substring. Subscript indices and annotations do not own the
assignment, while `<<=` and `>>=` remain assignment operators. Comparisons
remain ordinary controls. Invalid local syntax is not promoted to a recognized
target by a marker-shaped substring alone.
The target check excludes subscript indices and keeps comparisons and public
Content-Type controls in their established paths. Runtime-valid identifier
spellings are compared in raw and NFKC form only for this local target check;
structured credential-label policy is unchanged. The parser charges scanning
and target inspection to the existing work cap and deadline. Earlier reports
called U+200C invalid, but the pinned Python runtime accepts U+200C and U+200D
in identifiers; current regression controls follow the runtime parser.
Complete plaintext credential records continue through the existing validated
redaction path. The local target guard defers records covered by that later pass;
structured early returns still check all surviving targets.
Original structured labels are inspected before assignment
rewriting so sibling sensitivity is preserved. Continuation scanning is linear;
literal parser resource failures become boundary rejections.
Original-source mixed records recognize CR, LF, CRLF, NEL and Unicode line/paragraph
separators, including dash-only YAML items with indented labels. Standalone
Basic/Bearer values include all indented continuations and retain ordinary
unindented following text. Constant string addition and expression-free formatted
fragments are inspected without executing supplied code; complete bracketed records
are inspected independently of surrounding prose, quotation, comments or Markdown.
Fragment discovery uses local quote/comment state, so a prose apostrophe or outer
quoted presentation cannot hide an embedded record. Unresolved computed literal
records, YAML scalar members and keyword-based records reject even when their
expressions contain no string constants. Scan and parse work have input-relative
bounds as well as the shared deadline. Ordinary assignments, Content-Type records,
MIME values and signed numeric literals retain their content.
Original quoted scalar line boundaries are inspected before YAML folding.
Mixed sequence members and folded plain scalar members receive the same computed
record checks as parsed YAML. Keyword associations are inspected independently of
callable spacing or parentheses; invalid computed assignment targets reject.
Quoted records are checked at their original placements with YAML quote escapes
decoded while physical line boundaries remain intact. Fallback scalar checks keep
indented first lines, explicit-key indicators and comments before flattening or
JSON extraction. Assignment targets require static name, attribute and subscript
bases; unresolved formatted targets reject without executing supplied expressions.
Malformed structured members retain comment-only lines regardless of indentation.
Recognized continuation whitespace is normalized only in the validation view;
retained ordinary source text keeps its original characters. Incomplete quoted
members receive original-source checks before extraction, while complete quoted
values retain their structured sanitization path.
Decoded quoted members and AST expressions use the same recognized whitespace
and physical-line validation view. Inline Markdown members are inspected before
extraction; an apparent quote closer cannot conceal an incomplete computation.
Structured parsing validates these records without rewriting the original label
associations. A supplied document may contain at most 10,000 scalar/container nodes;
excessive structural work rejects during scanning, and composition also checks the
shared deadline at each node. Private-key delimiters are scanned without overlapping
suffix searches; incomplete blocks reject before structural parsing, while complete
blocks retain original structural label associations until sanitization.
Parser-omitted comments are discarded; credential-bearing keys and decoded
labels use the same rule as values. Sanitization shares the routing deadline.

The pinned TypeSafe patch and attribution are preserved. Missing usage/prices
remain unknown; conservative UTF-8 packing is a bound, not measured usage.
Output planning reservations do not enforce provider output. A requested hard
output ceiling rejects before dispatch. Spending ceilings require verified input
pricing and zero output rate. Task spending/token ceilings require verified
whole-run execution limits and later host enforcement; planning estimates alone
cannot establish compliance.

Evidence uses synthetic public inventories, caller flows and loopback BAML
judgments. It establishes software behavior, not live latency, model quality,
professional suitability, production companion readiness or policy promotion.
Replan HOST, then LEARN/EXPERIMENT/PREPARE in dependency order. Independent live
quality evidence and real decomposition remain downstream work.
