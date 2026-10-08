# Review Verdict: AGREE

**Review Subject**: [`research/pre-gepa-review/plan-round2.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/plan-round2.md) (and identical [`plans/detailed-pre-gepa-repairs-20261005-1336.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md))  
**Charter**: [`research/pre-gepa-review/brief.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/brief.md)  
**Prior Report**: [`research/pre-gepa-review/round1-gemini.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/round1-gemini.md)  
**Delta Artifacts**: [`research/pre-gepa-review/delta-round2.diff`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/delta-round2.diff), [`research/pre-gepa-review/delta-round2.json`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/delta-round2.json), [`research/pre-gepa-review/reconciliation.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/reconciliation.md)  
**Lens**: Alternatives and Experimental Validity (Round 2 Delta Review)

---

## Executive Summary

The round 2 delta systematically resolves all three blocking findings from the round 1 Gemini review while introducing no regressions into the plan. The reconciliation dispositions faithfully adhere to owner decisions (retaining BAML as the call/contract mechanism, respecting harness decomposition, and preserving the conservative no-additional-critical-failures promotion constraint under the $2 guard). 

Crucially, the revised plan:
1. Re-anchors Work Package C as an **uncalibrated, descriptive baseline** comparing suitability judgments with observed candidate outcomes and always-admit controls, rather than claiming to calibrate or prove JEV discrimination.
2. Directly mandates populating [`JudgmentRecord.measurements`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/contracts.baml#L221) with sanitized observations across default and injected adapters without double-booking spend.
3. Explicitly treats the BAML nullable bridge issue as an expected stop condition for Work Package B that cannot be cleared by numeric-only probe success, permitting Work Package A and offline Work Package C preparation to proceed independently.

No remaining blockers exist.

---

## Prior Findings Disposition Assessment

### Finding 1: Suitability discrimination calibration & baseline framing
- **Prior Finding**: The plan aimed to "distinguish useful suitability judgments from always admitting every model", yet froze the zero-shot prompt on candidate pairs historically admitted 100% of the time, guaranteeing degenerate collapse.
- **Reconciliation & Delta Assessment**: **Satisfied (Modified)**.
  - The reconciliation rightly distinguishes deterministic orchestration pre-filters from live JEV suitability discrimination, noting that candidate rejection does not abort the entire route if another candidate is admitted.
  - The delta amends the task statement and WP C (lines 8, 98, 116) to designate the experiment as an uncalibrated, descriptive baseline. It introduces pre-registered candidate-level joins, comparison against always admitting all eligible candidates, and offline opposite-usefulness controls.
  - This conforms to owner decisions without introducing fabricated discriminative power claims.

### Finding 2: `JudgmentRecord.measurements` capture & projection
- **Prior Finding**: [`src/jevdrill/integrations/jev.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/integrations/jev.py#L105) hardcoded `"measurements": []`, disconnecting JEV usage from replay bundles.
- **Reconciliation & Delta Assessment**: **Satisfied (Accepted with precision)**.
  - WP B changes (lines 61–63) and acceptance criteria (line 146) now mandate that `JevAdapter.judge()` attaches sanitized per-call measurements to successful records, and that [`src/jevdrill/application.py`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/application.py) projects them into decision details for both default and injected adapters as two views of the same observation (never additive).
  - Explicit provisions protect import boundaries (the adapter must not import `telemetry`) and ensure known observations survive failure paths where no complete `JudgmentRecord` is returned.

### Finding 3: Sampling non-determinism & paired critical regressions
- **Prior Finding**: Single-draw non-deterministic completions confounded model stochasticity with routing policy degradation under the paired critical failure rule.
- **Reconciliation & Delta Assessment**: **Satisfied (Modified)**.
  - The reconciliation correctly notes that temperature zero is neither universally supported across providers nor a guarantee of deterministic execution.
  - The delta freezes supported provider settings and seeded arm ordering, while mandating reporting of same-model fixed/routed contrasts as sampling diagnostics (line 116).
  - It maintains the owner's conservative no-additional-critical-failures promotion gate as an operational policy safeguard without asserting unsupported causal claims.

---

## Assessment of Rejected / Modified Recommendations Against Owner Decisions

1. **Gemini Alternative 1 (Decouple BAML response types to JSON Schema alone)**:
   - **Disposition**: Rejected.
   - **Assessment**: Correct. The owner decision explicitly mandated that "BAML remains the call/contract mechanism." The plan's retention of BAML-authored types with companion constraints, strict raw JSON parsing in the worker before semantic grading, schema derivation parity checks, and isolated private SDKs directly implements the owner's directive without sacrificing validation rigour.
2. **Gemini Recommendation 2 (Pre-specify unknown-cost study requirements)**:
   - **Disposition**: Accepted.
   - **Assessment**: Correct. Detailed runner amendment criteria (authorization binding, unresolved fixture, observable counters, reservation formula, ledger cap) are now specified in WP B (lines 70–71, 91).
3. **Gemini Recommendation 3 (Boundary conditions and 12-group uncertainty)**:
   - **Disposition**: Accepted.
   - **Assessment**: Correct. Evaluated uncertainty is explicitly bounded at the 12 semantic group level rather than 36 independent trials (line 116).

---

## Delta Regression Analysis

The delta additions across all sections were examined for regressions:
- **Immutable Replay Snapshots (lines 19, 120)**: Protects historical evidence integrity by copying study-bound source and generated files before implementation and verifying against `verification.json`.
- **Worker-Level Coercion Controls (lines 29, 54, 145)**: Requires testing that structural coercion is rejected in the actual worker before semantic grading, addressing BAML normalization vulnerabilities.
- **Counter Reconciliation Table (lines 56–64, 77–84)**: Formulates unambiguous per-counter precedence between direct and event observations, treating conflicts as diagnostic unknowns.
- **Explicit Bridge Stop Definition (lines 50, 71, 146)**: Explicitly documents that WP B expects to block on the known nullable bridge limitation and that a numeric-only success cannot close WP B, keeping unknown accounting intact while permitting WP A and offline WP C to proceed.
- **Candidate Truncation Guards (lines 86, 114)**: Pre-checks candidate/context bounds before freezing the schedule to avoid degenerate single-model runs.

No regressions or invalid scope expansions were introduced by the delta.

---

## Remaining Blockers

**None**. All blocking issues are resolved and properly bound to the acceptance criteria in lines 144–151.

---

## Files Actually Read

1. [`research/pre-gepa-review/round1-gemini.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/round1-gemini.md)
2. [`research/pre-gepa-review/reconciliation.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/reconciliation.md)
3. [`research/pre-gepa-review/delta-round2.json`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/delta-round2.json)
4. [`research/pre-gepa-review/delta-round2.diff`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/delta-round2.diff)
5. [`research/pre-gepa-review/plan-round2.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/plan-round2.md)
6. [`research/pre-gepa-review/brief.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/brief.md)
7. [`plans/detailed-pre-gepa-repairs-20261005-1336.md`](file:///mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md)

