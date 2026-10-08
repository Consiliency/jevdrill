## Verdict: PARTIALLY AGREE

The scope, spending controls, historical preservation, and deferral of GEPA are sound. Two planning gaps should be repaired before declaring the corpus and calibration protocol ready.

### Blocking findings

1. **The gold audit must cover mandatory semantic restrictions.**  
   The decimal-microunits task forbids floating-point multiplication, but its reference solution uses `Number(a)*1000000`. The reused grader checks only returned answers and input mutation. Thus a reference can pass the proposed shape checks while contradicting its supplied specification.

   **Acceptance affected:** package A’s trustworthy contract/reference freeze; acceptance criteria 1–2; the owner’s requirement to preserve mandatory quality checks.

   **Minimal repair:** explicitly audit each declared mandatory requirement against its grader. In the new corpus version, replace this reference with an implementation that avoids multiplication, preserve the numeric expected answers, and add a negative control that returns correct sample answers while violating the restriction. Leave historical artifacts unchanged.

   Evidence: [corpus.json:1948](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/corpus.json:1948), [existing grader:74](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/GEMMA-development-20261003/study.py:74), [plan:40](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md:40).

2. **Rejection frequency does not measure whether rejection helps.**  
   Package C requires rejection rates, selection variation, and downstream quality. These can describe arbitrary rejection without establishing useful suitability discrimination.

   **Acceptance affected:** the plan’s stated objective of distinguishing useful suitability judgments from always admitting every model; criterion 6’s frozen calibration criteria; the existing requirement to evaluate routing quality separately from downstream quality in [the specification:459](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/jevdrill-spec.md:459).

   **Minimal repair:** freeze candidate-level analysis joining each judgment to that candidate’s independent fixed-arm outcome for the same case. Report admitted/rejected observed successes and failures, missing outcomes, non-ready routes, and the always-admit comparison. Add offline fixtures with identical rejection rates but opposite usefulness. The existing five arms provide the necessary observations; no additional calls are required. Treat individual execution outcomes as noisy observations, not definitive suitability labels.

   Evidence: [plan:73](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md:73), [plan:88](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md:88).

### Recommendations

- Clarify line 74: a rejected **candidate** cannot be selected. A different admitted candidate may still produce a ready plan.
- Retain the existing seeded arm ordering and report uncertainty at the related-group level: there are 12 groups, not 36 independent cases.
- The GEPA claims are appropriately limited. These repairs can prepare development evidence; completion cannot establish readiness or promotion eligibility.
- Budget carry-forward, reservations for uncertain attempts, per-request dispatch records, immutable replay snapshots, and zero-dispatch replay are appropriate.

### Files actually read

Full files or relevant excerpts:

- [Review charter](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/brief.md)
- [Repair plan](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md)
- Routing-comparison evidence: [summary](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/summary.md), [usage diagnostics](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/usage-diagnostics.json), [protocol](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/protocol.json), [corpus](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/corpus.json), [objective analysis](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/objective-analysis.json), [controls](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/controls.json), [grading controls](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/grading-controls/controls.json), [verification](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/verification.json).
- [JEV BAML](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/jev.baml), [application excerpts](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/application.py), [evaluation excerpts](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/evaluation/pilot/evaluation-v2.py).
- [Contracts documentation](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/contracts.md), [route interfaces](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/route-interfaces.md), [specification excerpts](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/jevdrill-spec.md).
- Related historical runner code: [routing preparation](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/ROUTING-comparison-20261005/prepare.py), [routing controls](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/ROUTING-comparison-20261005/controls.py), [routing study](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/ROUTING-comparison-20261005/study.py), [provider study excerpts](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/PROVIDER-comparison-20261005/study.py), [independent grader excerpts](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/GEMMA-development-20261003/study.py).

Read-only review; no tests, edits, credentials, or provider calls.
