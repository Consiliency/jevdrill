# ROUTE replan: panel findings and reconciliation

## Result

The owner-authorized confirmation review completed with three usable reviewer
verdicts and a valid Astra president ruling. Gemini and Astra returned AGREE;
Grok returned PARTIALLY AGREE. The chair required two storage clarifications,
which are now incorporated into the plan and its SL-2 tests.

**Approved for implementation planning closeout by Codex self-review, as requested
by the owner.** The final F003/F004 edits satisfy the chair's required repairs.
No unanimous panel approval, implementation, phase completion or ratification
is claimed.

The three-round cap was declared before review. The board used Grok 4.7
(adversarial), Opus 5.5 (correctness), GPT-6 Astra (red-team), and Gemini 3.8 Flash
(alternative approach), with the runtime's Fable/Opus president route.

| Attempt | Reviewer outcomes | President / disposition |
| --- | --- | --- |
| Initial pointer preflight | Zero grounded reviews; Claude/Gemini could not read pointers; all legs failed tree authorization binding | Unusable; repaired input delivery |
| Round 1 | Grok/Astra/Gemini PARTIALLY AGREE; Opus stalled | Ruling format missing; final board unusable; individual findings preserved |
| Round 2 | Gemini AGREE; Grok/Astra PARTIALLY AGREE; Opus stalled | Valid REVISE ruling; repairs required |
| Round 3 | Gemini AGREE; Grok/Astra PARTIALLY AGREE; Opus stalled | Ruling format missing; final board unusable; individual findings preserved |
| Owner-authorized confirmation | Gemini/Astra AGREE; Grok PARTIALLY AGREE | Astra chair: repair F003/F004 before implementation; both incorporated and subsequently approved by owner-requested Codex self-review |

All seats finished before each reconciliation. No dissent was replaced by a
different reviewer. The runtime's final refusal can overwrite aggregate leg
statuses as UNAVAILABLE; individual `leg-*.verdict.json` files retain delivered
reviews and must not be confused with an accepted aggregate board result.

## Accepted repairs

- Additive discovery contracts and route-v2 wrapper; preserve old literals,
  fixtures and digest construction. Record the roadmap closeout amendment.
- Separate discovery policy/function identity and work-objective lifecycle from
  route suitability judgments and optimization metric identity.
- Rebind discovered guidance to concrete tasks, retaining trusted authority,
  exact revisions, mandatory instructions and existing zero/one/two combinations.
- Skip legacy catalog narrowing in linked routing and reject nested catalog_query.
- Explicit provider payload allowlist, bounded descriptions and text-free replay.
- Durable pre-dispatch reservations, atomic lifecycle deletion, linked commit
  checks and honest output-limit rejection.
- Explicit terminal-result precedence, including incomplete versus rejected
  searches and complete searches without feasible optional guidance.
- Extend the verifier to all seven ECs; old four-criterion evidence cannot pass.

The final round's status-gate, queue-order and stricter-constraint findings are
now fixed in the plan: success-only linkage before preparation/cache/retry/commit;
FIFO queues with deterministic alternation and width handling; field-wise
constraint ordering with negative tests. Recovery cannot dispatch new provider
work under an interrupted attempt. The authorized confirmation round cleared
these repairs. Its additional findings are reconciled below.

### Confirmation chair findings

- **F003, atomic recovery:** the plan now requires one transaction to recheck
  deletion/status and commit a terminal recovery result before any response.
  Late observations after terminalization are audit-only and cannot change
  the result, restore authority or release reservations. SL-2 must test races.
- **F004, independent ledgers:** each scoped idempotency key gets an independent
  append-only ledger and a fixed initial allowance. New requests do not inherit
  or clear another request's accounting; same-key recovery cannot replenish it.
  SL-2 must test new-key isolation and same-key recovery after a crash.

These are plan/verification requirements, not implemented behavior. The chair
required their repair before implementation; it did not approve the subsequent
text edits. No additional panel round was launched beyond the owner's allowance.

Nonblocking implementation reminders are retained: candidate-specific token
recounting, strict route-version discrimination, separate discovery policy
parsing, per-option provider-call accounting, task-time guidance rebinding and
preservation of the pinned TypeSafe patch. Existing plan requirements cover them.

## Recommendations reconciled using implementation evidence

- A planning reservation cannot enforce provider output. The pinned TypeSafe
  client has no output-token cap. Requested hard limits reject; other authorized
  discovery calls retain finite input, call and time bounds. Cost ceilings need
  supported pricing/bound evidence. The roadmap now states this explicitly.
  Astra and Grok accepted that correction in round 3.
- One unique objective lifecycle parent can own several immutable discovery
  attempts. Parent tombstoning invalidates all of them. Banning rediscovery
  under a new request key was unnecessary; round 3 accepted this repair.
- Category answers must affect traversal. Preferred/deferred queues preserve
  that behavior while leaving opportunities to recover from classification errors.
- The suggested docs ownership overlap was a review-summary abbreviation;
  the plan lists disjoint exact paths, not overlapping docs globs.

## Evidence and next action

Evidence: `research/roadmap-review/route-replan-20261007/`, including input
manifests, frozen bundles, individual verdicts, aggregate results and the round-2
president ruling. Detailed delta: `plans/route-review-delta.md`.

Planning checks: dispatch literals valid, roadmap hash matched, diff whitespace
check passed. Product tests/builds were not run for this planning task.

The owner approved the changed board and additional confirmation round. The
working routes delivered all three reviews and a valid Astra ruling. Evidence
is under the `confirmation/` subdirectory, including the explicit board authority.
The owner then requested self-review and a commit if approved. That review found
no blocking plan defect. F003 requires transactional terminal recovery, status and
tombstone checks, immutable results and audit-only late observations. F004 fixes
each attempt's initial allowance, isolates new keys and prevents retry budget
replenishment. These rules fit the existing transactional decision/deletion
pattern in `src/jevdrill/storage.py`; SL-2 explicitly requires their race, crash
and isolation tests. Discovery storage itself remains to be implemented.

Next: implement ROUTE's five serial lanes, preserving unrelated work and all
seven acceptance criteria. Unanimous panel approval remains unclaimed; no
runtime/adapter repair or further model benchmark is required for this closeout.
