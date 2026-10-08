# Round 2 methods review

## Verdict: AGREE

Both round 1 methods blockers are resolved in the revised plan. I found no new in-scope methods blocker in the recorded delta.

Reviewed plan SHA-256: `eb04c6b8475b9274afc946a33230451133c83083b182a729d5228a920d4d399a`. The saved plan's hash matches `delta-round2.json`.

## Resolution of prior findings

1. **Mandatory semantic restrictions and gold controls — resolved.** Package A now requires a requirement-to-grader audit across all 20 groups / 60 cases, a violating control for each mandatory requirement, and a freeze stop when a mandatory check is unsupported. It explicitly repairs the decimal-microunits reference through decimal digit assembly, preserves numeric expected answers and historical artifacts, and requires a correct-output implementation that violates the restriction to fail. The revised first acceptance criterion includes these obligations.

2. **Suitability usefulness analysis — resolved.** Package C now pre-registers candidate-level joins to independently graded fixed-arm outcomes, admitted/rejected observed passes and failures, missing and transport outcomes, non-ready routes, coverage, and comparison with always admitting eligible candidates. Equal-rejection/opposite-usefulness fixtures test the analysis. The sixth acceptance criterion requires this descriptive analysis and its controls. Individual executions remain noisy observations, and absent failures or rejections cannot establish calibration success.

## Other reviewed changes

- Candidate rejection is now correctly scoped to that candidate; another admitted candidate may yield a ready plan.
- Provider-supported sampling settings and seeded arm ordering are frozen. Same-model disagreements remain sampling diagnostics, and uncertainty is interpreted at the 12-group level. These provisions support a descriptive baseline without claiming powered discrimination or causal routing effects.
- Freshness requires new semantic groups, and exposed calibration material remains separate from release evaluation. Completion does not establish GEPA readiness or policy eligibility.
- Per-request reservations, explicit non-ready outcomes, immutable replay diagnostics, and historical source snapshots preserve the experiment's spending and evidence constraints. A budget stop must retain its actual outcome status.
- The known nullable bridge stop remains explicit. Numeric-only success cannot close package B; its blocker can coexist with completion of package A and offline package C. Live execution still requires the stated metering condition or a separately adopted limited unknown-cost amendment.

This is agreement with the amended planning design. Implementation acceptance and the separate governed review gate remain unresolved until their required evidence exists.

## Files actually read in round 2

- [reconciliation.md](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/reconciliation.md)
- [delta-round2.diff](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/delta-round2.diff)
- [delta-round2.json](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/delta-round2.json)
- [plan-round2.md](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/plan-round2.md)

No tests, source edits, credentials, or provider calls. The only file created by this round is this report.
