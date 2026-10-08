# Detailed plan: prepare comparative calibration

## Task

Carry out the authorized next step by preparing a concrete comparison and
checking what must precede production calibration. Comparator selection is
pending in the structured owner question. No new model call or paid allowance
is assumed while it is pending.

## Research summary

The existing local service provides Gemma generation and a Qwen embedding model;
metadata probes found no second generation model at the known local ports. The
completed development study retains 60 observations. The current policy evaluator
requires separately sealed policy holdout and regression splits, frozen quality
settings, mandatory-check success and four confidence bounds. Production adapter
acceptance separately requires three named operational checks; this development
comparison cannot substitute for them.

## Changes

- `.phase-loop/runs/CALIBRATION-readiness-20261003/prepare.py`: pure offline
  preparation, binding prior results/source/corpus, deriving descriptive quality
  checks and sample-size sensitivity from the existing evaluator. Prepare fresh
  balanced paired Gemma conditions with and without generic contract guidance.
- `.phase-loop/runs/CALIBRATION-readiness-20261003/test_prepare.py`: verify exact
  baseline prompts, guidance provenance, balanced ordering, unchanged grouping,
  threshold status and the evaluator's sample-size calculations.
- `evidence/EXPERIMENT/calibration-readiness-20261003/**`: draft paired protocol,
  quality-readiness report, concrete recommendation, source bindings and scoped
  verification. No production threshold, promotion authority or enabled study.
- `plans/manifest.json`, `.dev-skills/handoffs/**`: scoped lifecycle and handoff.

Read allowance: owned preceding paths; prior purpose-built Gemma protocol,
results, analysis and verification; prepared corpus; public evaluation/analysis,
local BAML transport and native EXPERIMENT reducer; hash-only prior study ledgers;
the three operational test names and local endpoint metadata. Existing native
evidence, paid proposals, public code and prior studies remain unchanged. No
credentials, logs, user tasks, serving changes, holdout or publication.

## Documentation impact

The recommendation distinguishes guidance comparison from model comparison,
development acceptance from production promotion, and data-derived uncertainty
from owner-selected quality requirements.

## Dependencies and order

1. Preserve status, public source and prior study hashes.
2. Prepare paired prompts, grouping, evaluator sensitivity and blocking checks.
3. Verify offline and preserve the concrete proposal for comparator selection.
4. Execute only a separately frozen protocol after that selection; the preparation
   plan itself performs no inference and claims no full phase acceptance.

## Verification

`.venv/bin/python -m pytest -q .phase-loop/runs/CALIBRATION-readiness-20261003/test_prepare.py`

`.venv/bin/python .phase-loop/runs/CALIBRATION-readiness-20261003/prepare.py`

Compile and Ruff F checks for the owned preparation files; whitespace, prior
study/public source hash and dirty-path audits. Full native suites are reused
only for their unchanged public inputs; no phase verdict is changed.

automation.suite_command: .venv/bin/python -m pytest -q .phase-loop/runs/CALIBRATION-readiness-20261003/test_prepare.py

## Acceptance criteria

- [x] The draft contains fresh paired calls for all 60 tasks, exactly preserves
      baseline prompts, groups related variants, balances order by group and
      records guidance as developed from exposed data.
- [x] Quality readiness reproduces observed task-family outcomes and the actual
      evaluator's uncertainty formula without declaring production thresholds.
- [x] Concrete execution choices and all three production operational checks
      remain explicit; no paid or local generation, promotion or holdout occurs.
- [x] Existing study bytes and public source bindings remain unchanged; all new
      output is owned by this plan and has executable verification evidence.
