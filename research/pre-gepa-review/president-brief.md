# President ruling: pre-GEPA repair plan

Act as the returning Opus correctness reviewer for the final round-3 delta and then as board president for this manual advisory review. Use read tools, without edits, tests, credentials, or experiment calls. The governed attempt failed before delivering usable reviews; this ruling cannot clear that gate.

Read:

- `research/pre-gepa-review/brief.md` (scope and owner decisions)
- `plans/detailed-pre-gepa-repairs-20261005-1336.md` (current plan)
- `research/pre-gepa-review/reconciliation.md` (finding dispositions)
- `research/pre-gepa-review/delta-round3.json` (reviewed plan hashes)
- `research/pre-gepa-review/delta-round3.diff` (wording repairs since your last verdict)
- `research/pre-gepa-review/round2-claude.md`
- `research/pre-gepa-review/round2-gemini.md`
- `research/pre-gepa-review/round2-methods.md`
- `research/pre-gepa-review/round2-redteam.md`

The three round-2 AGREE verdicts are carried; only your remaining dissent needs delta review. Read original reports or code only to resolve a concrete remaining conflict. First assess whether the checkpoint/test-suite wording resolves your last blocker, then rule as president on whether the reconciled plan is ready for bounded implementation, including its explicit evidence-dependent stops. Distinguish plan approval from completed metering, paid-experiment authorization, GEPA readiness, policy promotion and governed-gate passage.

In particular, package B explicitly expects to stop if the pinned bridge cannot handle nullable usage. Numeric-only success cannot close it. A and offline C may proceed. Do not waive this stop or require its implementation to be completed as a condition of approving a plan that records it.

Return a round-3 reviewer verdict and a president verdict, each AGREE, PARTIALLY AGREE, or DISAGREE; identify any surviving blocker by acceptance criterion; explain whether rejected/modified feedback was reasonably reconciled; name the next bounded action and what must remain pending. List the files actually read. Keep the ruling concise. The review loop cap is three rounds; do not expand this into a new roadmap or an optimization project.
