# Roadmap v1 board review and reconciliation

Status: reopened manual Gemini/Opus review and a separate Opus president pass completed. The president's required C1 correction is applied; both round-2 delta reviewers returned AGREE. Roadmap lint passes. CONTRACT planning is ready, with required follow-up inputs preserved. The earlier capped runtime review remains failed. This is not a ratified review or implementation acceptance.

## Scope and method

Requested: independent roadmap review with a board president, followed by reconciliation. Used the agent-harness advisor-board runtime and subscription CLI seats: Claude Opus 5.5 (correctness), GPT-6 Astra (red-team), Grok 4.7 (adversarial), and Gemini 3.8 Flash (alternative approach). President selection used the runtime's configured availability ladder, beginning with the Anthropic/Fable seat.

The project directory has no Git metadata. Reviews ran against isolated temporary Git snapshots, not a newly initialized project repository. No project commit, external release, or canonical adoption occurred. The review cap was declared before launch: three board attempts, including the initial snapshot-binding failure. Review findings and runtime failures are recorded separately.

## Attempt history

1. Initial snapshot had staged files but no commit. Review sandbox rejected its tree marker; all seats were unusable and the president produced no usable ruling. No approval is carried from this attempt.
2. Corrected committed snapshot yielded usable Gemini/Grok AGREE reports and Astra PARTIALLY AGREE. Astra found no roadmap blocker but noted omitted original draft/proof files and missing expected instruction files. Claude stalled. The president again returned `president_ruling_missing:president_invocation_failed`; the aggregate result was unusable despite the saved individual reports.
3. Final snapshot includes original files at their actual paths, the revised roadmap, a bound diff, and prior reports. A requested two-seat delta invocation was refused before seat execution because president mode requires all four seats. The final round therefore reran the full board with a smaller entry packet. Gemini and Grok returned AGREE; Astra returned PARTIALLY AGREE solely because expected instruction filenames were absent; Claude stalled with no usable verdict. The president again failed with `president_ruling_missing:president_invocation_failed`. The runtime marked the aggregate unusable; individual usable reports remain preserved separately.

The board runtime's aggregate delivered-seat count is zero after president failure. It must not be substituted for the independently saved seat results or interpreted as a completed approval. No disagreement triggered a substitute president, and no stalled seat was treated as approval.

## Reconciliation

| Source | Finding | Resolution |
|---|---|---|
| Gemini, first usable round | Explicitly test numeric strings and nullable/omittable distinctions | Clarified EC-CONTRACT-1; strict validation remains required |
| Gemini, first usable round | Cover unavailable credential services on headless Linux | EC-LEARN-3 now requires pending-content retention, inbox notice and no plaintext archive fallback |
| Grok, first usable round | Experiment defaults could read as implicit enablement | EC-EXPERIMENT-1 explicitly conditions counts on enablement and standing authority |
| Grok, first usable round | Name guidance benefit among evaluation objectives | Added guidance-benefit assessments to EC-CONTRACT-4 |
| Grok, first usable round | Protect held-out evaluation from early tuning | EC-HOST-3 uses development/validation splits; PREPARE owns untouched holdout evaluation after threshold freeze |
| Astra, first usable round | Snapshot omitted original draft and runnable proof fixtures | Included them in final snapshot; historical test outcomes remain reported observations, not independently reproduced results |
| Gemini, final round | Include whitespace variants in numeric-string tests | Carry to CONTRACT lane planning under EC-CONTRACT-1; no new roadmap goal needed |
| Astra, final round | Expected `review-instructions.md` and `review-bundle.md` absent despite a matching review-brief digest | Review-runtime packaging limitation remains unresolved; no unconditional sign-off claimed |

Those changes preserve phase aliases, interface gates, 21 EC IDs, open gate status and accepted JD decisions. The usable runtime reports established no substantive blocker within their review scope. The subsequent manual review below found gaps in unchanged text and upgraded the policy-evaluation holdout concern.

## Manual Opus review and president reconciliation

At the user's explicit request, launched Claude Opus 5.5 directly with a short file-pointer brief and Read/Glob/Grep tools. The process completed successfully. Its [verbatim report](../research/roadmap-review/manual-claude/review.md), [launch metadata](../research/roadmap-review/manual-claude/launch.json), and [brief](../research/roadmap-review/manual-claude-brief.md) preserve the reviewed inputs and limitations. Claude performed both correctness review and president reconciliation; no independent second president or cross-vendor review of its new findings is claimed.

Verdict: **PARTIALLY AGREE**, conditional on B1–B4 before CONTRACT planning. Accepted and applied:

- B1: cover unchanged original-draft requirements alongside JD decisions, mapping to EC IDs or explicit deferrals and verifying again in PREPARE.
- B2: freeze request envelopes, route requests and retry links, capability diagnostics, CLI exit/cancellation behavior and version compatibility.
- B3: require Python and non-Python acceptance/rejection parity using shared fixtures, with named validators for rules schemas cannot express.
- B4: require pinned bridge/generated-package verification on Linux/macOS/Windows for every supported Python version before contract freeze.

R1–R8 remain explicit CONTRACT coverage obligations: failed-acceptance rerouting; JEV fallback/privacy/token limits; guidance context and lifecycle; dependency readiness/import/scan semantics; explanations/settings precedence; export/import/recovery; platform lifecycle evidence; policy evaluation separated from release holdout. CONTRACT must map and amend affected ECs before those phases are planned. No `coverage.json` or platform evidence is fabricated during this reconciliation.

Optional O1–O8 remain available in the report for detailed planning. Astra's packaging concern remains part of its historical verdict but is not treated as a roadmap content defect. The manual ruling does not overwrite failed runtime aggregates or retroactively ratify the changed roadmap.

## Reopened manual panel

After sandbox restrictions were lifted, both requested manual CLI reviews produced usable reports against the same roadmap hash. Gemini 3.8 Flash (High) returned AGREE; Opus 5.5 returned PARTIALLY AGREE. A separate Opus invocation acted as president and returned PARTIALLY AGREE, requiring C1 before CONTRACT planning. These are two requested reviewer seats and a president invocation of the same model as one reviewer, not three independent vendors.

- [Gemini report](../research/roadmap-review/manual-rerun/round1/gemini-review.md).
- [Opus report](../research/roadmap-review/manual-rerun/round1/opus-review.md).
- [President ruling](../research/roadmap-review/manual-rerun/round1/president-review.md).
- [Reviewed snapshot](../research/roadmap-review/manual-rerun/round1/reviewed-roadmap.md) and [follow-up delta](../research/roadmap-review/manual-rerun/round2/delta.diff).

Applied C1: EC-CONTRACT-4 now requires mappings to criteria whose text verifies each requirement, amendments through closeout, and contract-level findings resolved before IF-0-CONTRACT-1. All 21 IDs remain open and unchanged. The president rejected C2 as a roadmap blocker but required it in the CONTRACT plan, alongside C3–C7. Scope notes preserve these inputs and P1–P7 as owner/phase-tracked coverage work.

Required CONTRACT plan inputs cover future contract parity checks, report acknowledgments, experiment transitions, named-validator fixture semantics, quality floors/regression tolerances, and owned open questions. P1–P7 cover ROUTE platform checks, attachments, host notices, stale-policy revalidation, early retention opt-out/deletion, policy-admitted guidance, and consistent platform evidence paths. Their detailed definitions remain in the Opus report; the president's dispositions control priority. None is recorded as implemented evidence.

Both reviewers checked only the new delta in round 2 of the declared three-round cap and returned AGREE: [Gemini](../research/roadmap-review/manual-rerun/round2/gemini-review.md), [Opus](../research/roadmap-review/manual-rerun/round2/opus-review.md). Gemini supplies the requested cross-vendor check of C1; Opus confirms its resolution and finds no delta blocker. The review converged in two rounds. No older verdict is promoted to fresh approval.

Applied Opus's nonblocking navigation suggestion after those verdicts: link the full finding definitions and reviewed snapshot, state that the president's ruling controls disagreements, and clarify that owners remain to be recorded during CONTRACT. This final reference/wording edit was locally checked, not separately sent for another panel vote. All implementation criteria remain open.

## Evidence and verification

- [First usable round seat reports](../research/roadmap-review/round1/).
- [Final round reports, delta and content bindings](../research/roadmap-review/final/).
- [Final aggregate failure](../research/roadmap-review/final/board-result.json).
- [Initial failed binding result](../research/roadmap-review/failed-binding/round1.json).
- `phase-loop validate-roadmap specs/phase-plans-v1.md` passes after reconciliation; repository-coherence checking is skipped because the workspace has no Git metadata.
- Roadmap remains within the 3,000-word budget. No builds, generators, migrations, tests or live JEV calls were run by the driving agent during roadmap reconciliation.
- Reviewers' statements about checks are attributed to their reports. One Grok report independently consulted release metadata; that does not constitute governed research or cross-vendor ablation evidence.
- Cross-vendor ablation was not performed. Board review and plan ratification must not be conflated.

Next implementation planning target is CONTRACT, with B1–B4 now incorporated and R1–R8 carried into its coverage work. The requested manual review and president reconciliation are complete; formal runtime approval and ratification remain unclaimed. Git provenance must be resolved before implementation execution.
