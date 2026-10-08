# Review charter: pre-GEPA repair plan

Review the plan below using local read tools. This is a planning review, not an implementation request. Do not edit the checkout, run tests, access credentials, call providers, or inspect unrelated private runs. Give an independent verdict: AGREE, PARTIALLY AGREE, or DISAGREE. Identify concrete acceptance criteria or existing invariants for each blocking finding, with a minimal repair. Distinguish recommendations from blockers.

Plan: /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md

Supporting evidence and code (open only what is useful):

- /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/summary.md
- /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/usage-diagnostics.json
- /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/jev.baml
- /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/integrations/jev.py
- /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/telemetry.py
- /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/application.py
- /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/tests/contracts/test_jev_boundary.py
- /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/scripts/check_generated_contracts.py
- /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/contracts.md
- /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/route-interfaces.md
- /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/vocabulary.yaml

Owner decisions: BAML remains the call/contract mechanism. The executive harness owns decomposition after resource selection; it can request model routing per concrete task. No additional critical failures may be introduced by policy promotion. Current work is repair and calibration preparation, with GEPA deferred. Do not expand this plan into a complete skill-discovery API or a release roadmap.

Focus on actionable feasibility, strict structural validation versus BAML coercion, usage-source precedence and missing counters, suitability experiment design, privacy, immutable evidence, spending/replay safety, and whether the stated tests actually prove acceptance.

Review loop is capped at three rounds. Let all reviewers finish before reconciling. Carry only standing AGREE verdicts; re-review dissent against a recorded delta. A board president must reconcile conflicts and rule on the final plan. Findings outside scope become follow-ups. Surviving in-scope blockers remain explicit and cannot be waived by a majority vote.
