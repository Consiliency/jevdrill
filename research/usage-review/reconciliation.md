# Usage reporting plan: advisor reconciliation

## Status

Round 1 finished with four usable PARTIALLY AGREE reviews. Opus, acting as board
president, required five plan amendments. They are incorporated in
[the detailed plan](../../plans/detailed-usage-reporting-20261001-1610.md).
Round 2 found one remaining announced-event-drop blocker. The final round-3
Opus review agrees with its repair; the three round-2 AGREE seats are carried.
All four standing reviewer verdicts agree. Implementation remains unstarted and
all six acceptance criteria remain unchecked. This is a manual advisory review, with no
governed gate or release claim.

## Reviewers and launch route

| Seat | Model | Lens | Round 1 |
| --- | --- | --- | --- |
| Claude | Opus 5.5, max | Correctness | PARTIALLY AGREE |
| Codex | GPT-6 Astra, max | Red-team | PARTIALLY AGREE |
| Gemini | Gemini 3.8 Flash, high | Alternative approach | PARTIALLY AGREE |
| Codex backfill | GPT-6 Astra, max | Adversarial | PARTIALLY AGREE |

The original Grok seat was rejected by the subscription server: installed CLI
0.1.220 requires an upgrade to at least 1.0.13. No newer local copy was found.
A separate Astra session filled the adversarial seat. No global tooling changed.

The installed agent-harness runtime supplied panel result handling, subscription
environment scrubbing, print-route liveness and the self-PTY Claude TUI adapter.
The legacy `invoke_panel` custom-spawn seam was used for the explicitly requested
manual review; `invoke_board` refuses direct manual launches in its governed
path. Reviewers received compact path/hash manifests and local tools with the
owner-authorized full permissions. These permissions were scoped by task to
reading sources and writing their own reviews, not by a governed OS sandbox.
No API/gateway fallback or host-native substitute supplied a seat.

Gemini's first attempt failed argument parsing; the timeout was corrected to
`1800s`. The second attempt's response was lost because the operator wrapper read
an empty leftover file instead of stdout. That capture bug was fixed; a fresh
attempt produced the usable review. The lost response is not counted. The server
restart interrupted the president before its ruling; its exact Opus session was
resumed through the same self-PTY adapter. The completed ruling is
[here](round1/president/ruling-2.md). Raw credentials and TUI transcripts are not
stored in this review directory.

## Required amendments

| Amendment | Findings | Resolution |
| --- | --- | --- |
| A1 | RT-01, ADV-02, AA-05, C-3 | Record CLI-reported cumulative totals; exclude resume/fork structurally and reject observable ambiguity. Document compaction, internal subagents, suppressed collaboration, retries, unannounced notification filtering and total resets as uncertified coverage; announced drops invalidate capture. |
| A2 | RT-02, ADV-03, AA-03, C-1; AA-02 clarification | Permanent invalidation on rejected/non-protocol stdout or reader/drain failure. Distinguish EOF and errors; drain both streams. Validate authoritative keys strictly while treating other item content as opaque; accept the real web-search duplicate-ID shape. |
| A3 | ADV-01 | Timeout/stall reports failed even when shutdown exits zero. Keep observed counters and existing applied identity; interruption still reports canceled. Add graceful timeout/stall controls. |
| A4 | C-2 | Private default-false `codex_usage_capture` opt-in passed by the bound adapter. Ordinary operator `--json` cannot enable probing or split capture. Add a default-path control. |
| A5 | C-4 | Require launch seam, real completion-proof/stdin and LaunchSpec suites alongside liveness/supervision. Require their designated controls in evidence reduction. |

## Final delta: announced drops

Round-2 Opus finding R2-1 was verified against the newly pinned `exec/src/lib.rs`.
Exec emits an error item when its in-process event channel lags. The final plan
permanently invalidates capture on that exact lag/drop message prefix and the
existing reroute prefix, reading only one string message from error items. It
requires the lag-notice-then-valid-terminal negative control, splits announced
loss from unobservable residuals, accepts the fifth native usage key without a
new metric, and preserves existing test authority controls when updating mocks.
Round-3 Opus confirms that repair and the three carried agreements remain valid.

## Other findings

- **RT-03 / AA-06:** clarify failure without a valid terminal snapshot versus
  failure after one. Preserve applied identity; failure alone does not mean the
  selected plan was not applied.
- **AA-01:** retain the BAML-shaped host-local receipt. Existing
  `LaunchResult.jevdrill_execution_run` is the same pattern; no published invariant
  requires a second generic token type. The adapter still validates the existing
  contract before reporting.
- **AA-04 / C-6:** defer version-probe caching. Keep current host-monotonic
  launch-call timing, including preparation and the probe; document that scope.
  Selective subtraction would change the metric inconsistently.
- **C-5:** a known zero means zero reported by the CLI. It is not independently
  established provider absence or invoice data. Document the distinction.
- **C-7:** adopt same child environment/PATH, owned probe process-group cleanup
  and bounded pipe shutdown within the existing launcher boundary. Keep recorded
  executor argv unchanged; no executable-identity claim is added.
- **C-8:** reject the pinned observable model-rerouted notice as ambiguous usage.
  Fixing immutable model attribution remains separate work.
- **C-9:** defer runner billing-classifier repair to a separate bounded change.
  Generic substring matching can misclassify JSON containing `usage`; this also
  affects existing operator JSON runs. It does not control JEV lifecycle and
  `runner.py` is outside this plan. No claim is made that this issue is fixed.
- **N-1:** record local-to-upstream file mapping in new verification metadata;
  preserve the historical planning copies and input records.
- **N-2:** retain existing `unknown/not_reported` compatibility in this change.
  Richer unknown reasons are optional follow-up work, not a new wire requirement.
- **N-3:** fix the propagation wording: Linux ephemeral monitoring is local;
  Linux lease-supervisor recursion carries the observer; Windows stays unknown.

Additional pinned source inspection confirmed `exec/src/lib.rs` filters usage
updates to the active root thread and turn (dispatch at 1280; predicate at 1636).
The copy and commit/hash metadata are in [upstream/](upstream/inputs.json).
That filtering establishes attribution, not complete internal accounting.

## My recommendation

Implement the revised bounded plan after the delta review settles. The required
changes close identifiable parser, opt-in, lifecycle and verification gaps while
keeping BAML, the durable queue, metric definitions and the two runtime-file
boundaries. Input accounting, prices, provider invoices, complete child totals,
runner classifier repair and model-attribution repair remain separate work.

## Evidence and limits

Reviewers performed source inspection. No implementation tests, builds, fixture
executions, policy promotions, commits or deployments ran. Historical V0/pilot/
Gemma evidence and exhausted live-study ledgers remain unchanged. Review calls
were separately authorized by the owner's panel request.

- [Round 1 input bindings](round1/bindings.json)
- [Round 1 consolidated reviews](round1/consolidated-result.json)
- [President ruling](round1/president/ruling-2.md)
- [Round 2 delta](round2/delta.diff)
- [Final delta and binding](round3/delta-binding.json)
- [Final standing verdicts](round3/consolidated-result.json)
- [Final Opus review](round3/claude/verdict.md)

The reconciliation text supplied to rounds 2/3 is preserved at
`round2/reviewed-reconciliation.md`; this status update follows review completion
and changes no reviewed plan or runtime source.

Final optional suggestions: include a nonmatching genuine error-item positive
fixture to guard the narrow notice match; use the native five-key shape in the
installed conformance child. The latter is already implied by the plan. Neither
adds a gate or extends the three-round loop.
