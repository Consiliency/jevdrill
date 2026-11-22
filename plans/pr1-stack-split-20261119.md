# Split of Consiliency/jevdrill#1 into a reviewable stack

Status: plan, owner-directed on 2026-11-19. Execution starts after the R43 bounded proof.

## Why

Consiliency/jevdrill#1 (`codex/implementation-reviewed`) holds ROUTE discovery and the offline HOST, LEARN and EXPERIMENT runtimes. It has 484 files, about 198k added lines and 76 commits. It cannot reach merge in its current form:

- **Round 5 BLOCK_MERGE.** Credentials could reach judges and retained artifacts. Since then, each of 42 repair/proof/review rounds has found new sanitizer bypasses.
- **R32.** The original review history is unrecoverable. Every whole-PR review must weigh that loss, and the last fresh panel (R41) produced no usable votes.

The owner chose to split the PR into a stack. Each PR gets a fresh review with complete history, under a review board whose president is **Fable 5.2**, to stop open-ended churn and scope creep.

## What the 198k lines are

| Kind | Approx. added lines | How it is reviewed |
| --- | ---: | --- |
| Generated BAML SDK (`src/baml_sdk`) and exported schemas (`schemas/`) | 63k | Reproducibility: the pinned compiler regenerates them byte for byte (`scripts/check_generated_contracts.py`). They are not read line by line. |
| Phase evidence and review records (`evidence/`) | 91k | Not merged as new acceptance. The current evidence for each PR is produced fresh by its verifier. |
| Hand-written source (`src/jevdrill`) | 12k | Read in full. |
| Tests | 22k | Read in full. |
| Scripts and workflows | 4.6k | Read in full. |

Internal imports are acyclic. `contracts` is the base; most domain modules depend only on it; `context` (the sanitizer) depends only on `contracts`; `application` depends on everything.

## The stack

Each PR is cut from `codex/implementation-reviewed` at the R43 head (`94475ba29`). It is based on the PR below it, carries its own tests and verifier, and must keep `main` green except for checks documented as owned by a later PR. No behaviour is rewritten during the split. A change found necessary during review is made in that PR, in scope.

1. **S1 — Contracts and generated SDK.** `baml_src/`, `src/baml_sdk/`, `schemas/`, `contracts.py`, `telemetry.py`, `tests/contracts/`, the contract scripts and vocabulary docs. Acceptance: reproducible generation and CONTRACT native results on Python 3.14 for Linux, macOS and Windows.
2. **S2 — Storage and leaf domain modules.** `storage`, `catalog`, `inventory`, `settings`, `costing`, `guidance`, `routing` and `evaluation`, with their tests. This includes `research/evaluation/cases.json`: per the owner's 2026-11-19 decision it is already public and lands as a development fixture, which turns the Linux catalog check green.
3. **S3 — Context sanitizer.** `context.py`, `tests/context/` and `tests/privacy/`. Its design review comes before the code review: the board first rules on the approach (continue pattern-based redaction, or fail closed by withholding any field that has credential-like material) and states the threat model. This PR resolves the round-5 credential blocker on its own terms.
4. **S4 — Offline LEARN and EXPERIMENT runtimes.** `analysis`, `experiments`, `maintenance`, `integrations/{archive,experiments,development}`, their tests, and the experiment, promotion and retention suites.
5. **S5 — ROUTE application.** `discovery`, `application`, `cli`, `integrations/jev`, the application, CLI, discovery, conformance and integration tests, `verify_route_phase.py` and `route.yml`. Acceptance: the ROUTE verifier (EC-ROUTE-5–7) passes natively on Python 3.14.
6. **S6 — Phase verifiers and records.** The HOST, LEARN and EXPERIMENT verifiers and their workflows, and a pointer document to the archived #1 review record. HOST and LEARN native receipts on Python 3.14 come from the owner's hosts.

Workflows introduced by the stack are pinned to commit SHAs with explicit least-privilege permissions, following Consiliency/jevdrill#3.

## Review board

- **Seats:** correctness, security/privacy, and one alternate vendor. Each reads only its PR's diff, its stated acceptance criteria and the code it calls.
- **President: Fable 5.2 (`claude-fable-5-2`).** The president:
  - fixes the scope before review starts: the PR's files and acceptance criteria, nothing else;
  - rules each finding as a blocker, an in-scope fix, or out of scope. Out-of-scope findings become backlog issues, not blockers;
  - allows at most **two review rounds per PR**. Round 2 checks only round-1 blockers and the fix diff. Ruled items are not re-opened unless the fix itself regresses them;
  - may stop a PR and send it back to planning if it can't converge in two rounds.
- Seat or provider failures are recorded. A missing seat is replaced once; it does not restart the round.

## Record of #1

- When S5 merges, #1 is closed as superseded. The branch is kept and tagged `pr1-final-record`.
- Its review rounds, proof archives and R32 history stay where they are. Nothing is rewritten.
- The 36 exposed evaluation cases are never used as held-out evidence. A new private held-out set, kept outside git, is built for the EXPERIMENT and PREPARE quality claims.

## Order and dependencies

S1 → S2 → S3 → S4 → S5 → S6, reviewed in that order. S3's design ruling can run in parallel with S1 and S2 review. After S5, replan HOST, LEARN, EXPERIMENT and PREPARE against the amended roadmap, as `docs/roadmap-status.md` requires.

## Outcome

Recorded when the stack closed. The text above is the plan as directed on 2026-11-19 and is not edited.

| Plan item | Pull requests |
| --- | --- |
| S1 | Consiliency/jevdrill#12 |
| S2 | Consiliency/jevdrill#18 |
| S3 | Consiliency/jevdrill#27 |
| S4 | Consiliency/jevdrill#44 |
| S5 | Consiliency/jevdrill#54 (S5a) and Consiliency/jevdrill#66 (S5b) |
| S6 | Consiliency/jevdrill#76 (S6a, the offline calibration instrument) and Consiliency/jevdrill#85 (S6b, the record and the docs) |

S6 did not land as planned. Its HOST, LEARN and EXPERIMENT phase verifiers, their workflows and the HOST conformance tests are not on `main`: they need the agent-harness host integration, which is in draft in that repository (Consiliency/agent-harness#2071) and is not yet reviewed or merged. No Python 3.14 HOST or LEARN receipt was made, on the owner's hosts or anywhere else, and no HOST, LEARN or EXPERIMENT gate is claimed. Those files stay at the tag `pr1-final-record` and are inputs to the replan named in the last line of "Order and dependencies". See [roadmap status](../docs/roadmap-status.md) and [where the record of #1 is](../docs/pr1-review-record.md).
