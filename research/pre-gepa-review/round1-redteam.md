## PARTIALLY AGREE

The scope, BAML requirement, bridge stop condition, spending boundary, and preservation of historical evidence are sound. Three in-scope blockers need small plan amendments.

### Blocking findings

1. **Define usage reconciliation within one invocation.**  
   [Plan line 56](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md:56) makes direct usage authoritative but also makes conflicting counters unknown. It does not specify whether conflicts include direct-versus-event disagreement, whether fallback applies per counter, or how duplicate observations are associated with one call. Equal counters from two real calls must count twice.  
   **Acceptance:** line 113.  
   **Repair:** add a reconciliation table and invocation-scoped tests covering absent, partial, equal, and conflicting sources, plus two separate calls with identical counters.

2. **Require usage preservation when routing fails after a paid call.**  
   The application currently collects observations, but a judgment failure without fallback [raises before measurement projection](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/application.py:299); the [outer failure handler](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/application.py:364) returns details without those measurements. A first successful judgment followed by a second malformed response can therefore lose known usage. Boundary-only metering tests would miss this.  
   **Acceptance:** lines 113–114; [failed-attempt accounting invariant](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/evaluation-protocol.md:31).  
   **Repair:** explicitly test this sequence through `Application`, preserving known observations once, keeping uncertain usage reserved, and replaying without dispatch.

3. **Freeze a suitability scoring rule, not only rejection statistics.**  
   [Plan line 88](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md:88) requests rejection rates and selection variation. Those measures cannot distinguish useful discrimination from arbitrary rejection.  
   **Acceptance:** line 116’s frozen criteria; [calibration-against-outcomes invariant](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/evaluation-protocol.md:29).  
   **Repair:** predeclare how each candidate judgment will be compared with independently graded fixed-arm outcomes and an always-admit comparator. Report admissions/rejections by observed pass/fail and family; keep transport failures and insufficient evidence separate. The existing five arms supply these observations without additional calls.

### Recommendation

Add an explicit end-to-end negative control proving that the private comparison worker rejects raw structural corruption **before** BAML coercion can influence grading. The existing worker [grades normalized typed output](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/PROVIDER-comparison-20261005/study.py:167), so testing the new validator in isolation would be insufficient.

### Files read

Read the [brief](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/pre-gepa-review/brief.md), [plan](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-pre-gepa-repairs-20261005-1336.md), and **all eleven supporting files listed in the brief**. Additional full or excerpted reads:

- [Integration tests](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/tests/integrations/test_jev.py), [privacy tests](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/tests/privacy/test_jev_privacy.py), [application tests](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/tests/application/test_route_integration.py).
- [Specification](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/jevdrill-spec.md), [evaluation protocol](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/evaluation-protocol.md).
- Generated [ModelTurn definitions](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/baml_sdk/ai/__init__.py), [event definitions](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/baml_sdk/ai/events/__init__.py), [TypeSafe client definitions](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/baml_sdk/vendor/typesafeai/__init__.py).
- Historical routing comparison [protocol](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/protocol.json), [verification](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/evidence/EXPERIMENT/routing-comparison-20261005/verification.json), [generator](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/ROUTING-comparison-20261005/prepare.py), [runner](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/ROUTING-comparison-20261005/study.py).
- Referenced provider comparison [generator](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/PROVIDER-comparison-20261005/prepare.py) and [runner](/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/PROVIDER-comparison-20261005/study.py).

Also inspected scoped search hits in costing, contract decisions, generated exports, and application/privacy tests. No edits, tests, credential access, or provider calls. This is a manual advisory verdict, not governed runtime-board evidence.
