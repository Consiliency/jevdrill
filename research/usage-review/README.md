# Usage reporting plan review: complete

**The revised plan is ready for implementation.** Opus, Gemini and two independent
Astra reviewers have standing AGREE verdicts. The Opus board president confirms
that no plan-level blocker remains. This is a manual advisory review; all six
implementation criteria remain unchecked and no runtime tests ran.

- [Revised detailed plan](../../plans/detailed-usage-reporting-20261001-1610.md)
- [Reconciled findings and recommendations](reconciliation.md)
- [Final president ruling](round3/president/ruling-2.md)
- [Review closeout and bound plan hash](closeout.json)

## What changed in the plan

1. Describe CLI-reported totals and their accounting limits honestly.
2. Permanently reject malformed, truncated or observably incomplete capture;
   accept genuine web-search duplicate IDs inside opaque content.
3. Report timeout/stall as failed even after graceful exit zero.
4. Require an explicit adapter opt-in; ordinary operator JSON launches stay unchanged.
5. Require regression checks for the modified launch seam and completion proof.
6. Reject the pinned warning that announces dropped events, with a negative control.

Existing BAML wire contracts, metric definitions and the two runtime source-file
boundaries remain unchanged. The final plan hash is
`0727eabde2c75a7b097df8ff1d254c16150f0e6c332c90e5547060413b0e9d58`.

## Final standing reviews

| Reviewer | Lens | Verdict | Review |
| --- | --- | --- | --- |
| Opus 5.5 | Correctness | AGREE, fresh round 3 | [Report](round3/claude/verdict.md) |
| GPT-6 Astra | Red-team | AGREE, carried round 2 | [Report](round2/codex/verdict.md) |
| Gemini 3.8 Flash | Alternative approach | AGREE, carried round 2 | [Report](round2/gemini/verdict.md) |
| GPT-6 Astra | Adversarial | AGREE, carried round 2 | [Report](round2/codex_adversarial/verdict.md) |

The three carried agreements follow the bounded delta-review rules. This is not
four fresh reviews of the final head. Grok's installed CLI was rejected as
outdated; Astra supplied its adversarial seat. Claude used the runtime self-PTY
subscription TUI adapter. Gemini and the other seats were manually launched with
compact file pointers and tools, as requested. Full permissions were authorized;
this route supplies no governed sandbox attestation.

## Recommendation and remaining work

Implement the revised plan, then run its local fixture and installed transport
verification. Preserve existing worktree changes and historical V0/pilot/Gemma
state. No live-study budget was reopened. This review makes no deployment,
publication, policy promotion or implementation acceptance claim.

Runner billing-classifier repair and immutable model attribution remain separate
follow-ups. Accounting for input context, prices, provider invoices and complete
internal/child activity also remains outside this plan. Optional implementation
controls are listed in the reconciliation and final president ruling.

## Pinned source mapping

At `openai/codex` commit `ff6aec96948b70d94983af2641a6b67c94faeff5`:

| Local copy | Upstream path |
| --- | --- |
| PLAN run's `exec-events.rs` | `codex-rs/exec/src/event_processor_with_jsonl_output.rs` |
| PLAN run's `exec-contract.rs` | `codex-rs/exec/src/exec_events.rs` |
| PLAN run's `protocol.rs` | `codex-rs/protocol/src/protocol.rs` |
| [Additional review copy](upstream/inputs.json) | `codex-rs/exec/src/lib.rs` |

Original planning records and review inputs are preserved. The reconciliation
text seen by rounds 2/3 is archived at `round2/reviewed-reconciliation.md`.
