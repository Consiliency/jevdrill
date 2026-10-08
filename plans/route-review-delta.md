# ROUTE review reconciliation: round 1 to round 2

Base: round1/review-bundle.md and input-manifest.json under
research/roadmap-review/route-replan-20261007/. Round 2 binds the updated plan and
roadmap by content hashes in its own input manifest. No product code changed.

All three delivered reviewers returned PARTIALLY AGREE. Opus stalled. The
president response failed the format check; the runtime invalidated the final
board verdict. Individual leg verdict files preserve the useful findings.
No approval or carried AGREE verdict is claimed. All seats are being rerun.

## Repairs

- Astra/Gemini contract amendment: roadmap ROUTE closeout now explicitly permits
  discovery, route-v2 and discovery lifecycle interfaces via canonical_spec_update.
- All reviewers' task binding: exact discovered references restrict fresh host
  options; adapters rebind task_id, preserve authorized role/authority, retrieve
  and recount exact instructions, and preserve mandatory constraints.
- Grok's suggested empty/full-pair-only restriction is not adopted: existing
  zero/one/two optional combinations remain useful when tasks differ. Undiscovered
  options remain excluded, which addresses the underlying authority concern.
- Astra/Grok policy identity: separate DiscoveryJudgmentPolicy/Record use
  ObserveDiscoveryOption-v1; route JudgeCandidate-v1 contracts remain unchanged.
- Gemini/Grok scope: dedicated DiscoveryEnvelope/Scope/Inspect/Delete types keep
  old scope/envelope literals unchanged. Work lifecycle uses work_objective_id,
  distinct from the existing optimization metric's objective_id.
- Grok navigation: no catalog.narrow call in discovery; least-recently-served
  paths including deferred alternatives, stable ties, final-leaf support ordering.
- Grok terminal outcomes: explicit status table distinguishes all-rejected,
  missing answers, exhaustion, supported partial results and context/conflicts.
- Privacy/replay: explicit provider allowlist, persisted text-free transition
  facts, retention opt-out test and changed-live-catalog replay test.
- Budget/crash: immutable reserved discovery ID, same-key digest conflicts,
  no retry of uncertain calls, existing commit margin, honest output-limit
  rejection and transactional linked-deletion check.
- Astra objective fixture: fixed catalog with different objectives must produce
  different supported guidance, alongside the two-task integration case.

## Remaining review request

Review the repaired plan and the remaining interactions, especially separate
discovery scope, v1 compatibility, task guidance conversion and replay privacy.
No software implementation or native-platform evidence is claimed.

## Round 2 to round 3

Round 2: Gemini AGREE; Astra/Grok PARTIALLY AGREE; Opus stalled again.
The president delivered a valid REVISE ruling. Round 3 is the final planned
substantive review round. All reviewers receive the changed plan; no previous
AGREE is used to approve these new semantics automatically.

- F003: freeze true/false/unknown expansion and two-queue service. Instead of
  ignoring category answers until leaf selection, alternate preferred and deferred
  service, with stable ordering inside each. A test must prove changed category
  answers change traversal and alternate-domain recovery remains possible.
- F004/F005: route-v2 rejects catalog_query, skips narrow, substitutes restricted
  options before _prepare, uses exact six-field required-reference coalescing and
  accepts only equal/stricter task constraints. The selected-result refs are the
  allowlist; explanatory alternatives cannot enter.
- F006/F021: one permanent lifecycle row owns multiple immutable request attempts.
  Atomic parent tombstoning invalidates all retries/caches and blocks late commits,
  observations or attempts. This addresses resurrection without forbidding
  rediscovery under a new key while the objective is live.
- F011: default 2,048-byte description cap, only reducible. Exceeding it marks
  description unavailable; no silent truncation. A length cap is a packing rule,
  not a guarantee that metadata contains no instruction-like text.
- F018–F020: explicit status precedence; empty alternative is not positive
  evidence. Complete-but-infeasible optional guidance uses no_optional_guidance
  with explicit exclusion reasons, preserving feasible mandatory guidance.
- F007/F015/F017: inspected baml_src/ns_typesafe_patch/client.baml: constructor
  exposes model, credentials, endpoint, timeout and wire capture, but no output
  token cap. Requiring an enforced hard output allowance on every discovery call
  would make this plan unusable. Revised policy explicitly separates a planning
  reservation from nullable hard_output_token_limit. Unsupported requested hard
  limits reject before HTTP. Calls without such a limit retain finite input,
  call and time limits. Requested spend caps require supported price/bound
  evidence (known zero output rate on this adapter); missing prices otherwise
  remain unknown. A positive loopback test must exercise generated BAML without
  an invented provider cap. The roadmap now states this distinction explicitly.
  This changes no caller-requested constraint and asserts no real provider price.
- President F030's docs-overlap observation came from a reviewer shorthand:
  the actual SL-0 plan lists exact doc paths, not docs/*. Ownership stays disjoint.

Please adjudicate the bounded repairs against the actual declared guarantees.
If output enforcement remains required regardless of requested constraints,
identify the existing invariant requiring it rather than assume that a planning
reservation was a hard ceiling. Do not turn missing current implementation
artifacts into evidence that planned behavior already exists.

## Owner-authorized confirmation round

The owner approved one focused confirmation round after the original cap,
using Gemini, Grok and Astra as reviewers and Astra as president. This is an
explicit board change, not a silent fallback or a waiver of substantive findings.

Base: the round-3 frozen bundle and individual verdicts. Current plan changes:

- Only selected_guidance and no_optional_guidance may feed route-v2, including
  cache/retry/commit paths. Test every result variant with an otherwise feasible
  quality-sufficient candidate. Preserve uncertainty and termination metadata.
- Preferred and deferred queues are FIFO by monotonic enqueue sequence. Stable
  IDs order siblings at insertion. Alternate nonempty queues; retain excess
  frontier options as requeued cursors. No last-service re-sort remains.
- Define stricter constraints field by field, including the existing v1 meaning
  of an empty allowed_providers list. Reject relaxations/incomparable changes.
- Recovery of a nonterminal attempt never dispatches additional provider work.
  It reduces durable observations or returns interrupted failure; a new response
  deadline does not reset the original provider allowance.

Confirm these repairs and identify only concrete remaining EC/contract defects.
Implementation artifacts are future obligations, not evidence already produced.

## Confirmation outcome and final reconciliation

Gemini and Astra returned AGREE; Grok returned PARTIALLY AGREE. The authorized
Astra president delivered a valid ruling requiring F003/F004 repairs before
implementation. All reviewers agreed that the four confirmation repairs held.

F003 is now explicit: same-key recovery atomically rechecks tombstone/status and
commits its terminal result before returning; observations arriving after
terminalization are audit-only and cannot replace the result, restore authority
or release allowance. F004 is now explicit: each scoped idempotency key owns an
independent append-only ledger with fixed initial allowance; new keys neither
share nor inherit another attempt's remaining budget, and same-key recovery
cannot replenish it. SL-2 includes the corresponding race and isolation tests.

These final edits have not been re-reviewed. The authorized extra round is
complete; no unanimous final-artifact approval or implementation is claimed.

## Subsequent owner-requested self-review

The owner requested Codex review the changes and commit if approved. Codex
reviewed the final plan, roadmap coverage and existing transactional storage
boundaries. F003/F004 are satisfied by explicit atomic terminalization,
audit-only late observations and independent fixed-initial-allowance ledgers,
with race/crash tests assigned to SL-2. No blocking plan defect was found.
The final edits are approved for planning closeout; this records self-review,
not a new panel verdict or completed implementation.
