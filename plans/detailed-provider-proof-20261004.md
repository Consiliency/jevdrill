# Detailed plan: prove the approved low-cost provider paths

## Task

Run Google Gemini first, then Together, Groq, OpenAI and Cerebras using existing
1Password credentials and three purpose-built development tasks per provider.
The owner approved the cheap shortlist and suggested Cerebras. This is fresh,
narrow authority for these proofs; historical paid grants remain unchanged.
Use a conservative $2 raw token reservation ceiling, one call at a time, no
automatic retries, 2,048 output tokens and a 60-second local process guard.
No purchase, account change, promotion, sealed holdout or publication.

## Research summary

The current authenticated catalogs include all selected models. Cerebras offers
GPT OSS 120B and Qwen 3.8 27B; GPT OSS has lower published token prices. Existing
BAML 0.20.1 supports native Google and generic OpenAI-compatible clients. A
private generated BAML project avoids changing the product's frozen inputs.
The first three prepared corpus cases exercise implementation, clean-code
review and fact-preserving documentation. Existing independent grading checks
answers, input preservation, review labels/examples and supplied facts.

## Changes

- `.phase-loop/runs/PROVIDER-proof-20261004/**`: private BAML project, generated
  SDK, controller, offline HTTP fixtures, immutable protocol and attempt ledger.
  Model bindings: Google `gemini-2.5-flash-lite`, Together
  `Prism-ML/Ternary-Bonsai-27B`, Groq `openai/gpt-oss-20b`, OpenAI `gpt-6-luna`,
  Cerebras `gpt-oss-120b`. Read secrets only into memory; never persist request
  headers, raw errors or complete wire responses. Reserve a full catalog context
  and output cap per attempt until measured usage is known. Uncertain attempts
  retain their reservation and are never redispatched. Stop further requests to
  a provider after its first failed or incomplete call.
- `evidence/EXPERIMENT/provider-proof-20261004/**`: frozen public protocol,
  filtered observations, independent grades, descriptive analysis, summary,
  scoped verification and preservation/dirty-path classification.
- `evidence/ROADMAP/latest-study.json`: point to the actual development proof.
- `plans/manifest.json`, `.dev-skills/handoffs/**`: lifecycle and closeout.
- Skill reflections for the invoked planning and execution workflow.

Read allowance: the owned paths; public source, SDK and native evidence;
`evidence/EXPERIMENT/next-calibration-corpus.json`; prior provider inventory;
`.phase-loop/runs/PROVIDER-inventory-20261004/catalogs.json`;
`.phase-loop/runs/GEMMA-development-20261003/study.py` (reuse only its pure grading
helper with this run's custody lock); prior study protocols, analyses and
verification. Hash-only prior SQLite ledgers and local grant artifacts. The five
named provider credential items in Consiliency Deploy Secrets may be read into
memory without logging their payloads. Fixed official endpoints and public
pricing/model metadata may be inspected. No other private files are needed.

## Documentation impact

The study summary records capabilities, accounting provenance, latency,
failures and limits. Three exposed tasks establish execution capability and
specific outcomes; they cannot establish a quality ranking or replace the
production EXPERIMENT acceptance checks.

## Dependencies and order

1. Save starting dirty paths and hashes of public inputs and historical studies.
2. Compile the private BAML project; verify request shapes, secret redaction,
   strict grading, durable reservation and replay using offline fixtures.
3. Freeze the exact protocol before inference. Run Google first, then the other
   four providers sequentially; retain incomplete results without retries.
4. Re-run the scoped checks and prove replay adds zero calls. Preserve existing
   native verdicts and close out locally in the existing task-owned worktree.

## Verification

Private BAML `check` and `generate`, using the pinned 0.20.1 toolchain.

`.venv/bin/python -m pytest -q .phase-loop/runs/PROVIDER-proof-20261004/test_study.py`

`.venv/bin/python .phase-loop/runs/PROVIDER-proof-20261004/study.py controls`

`.venv/bin/python .phase-loop/runs/PROVIDER-proof-20261004/study.py run`

Replay the run with the same frozen protocol and verify zero redispatches.
Compile, Ruff F, whitespace, secret-canary, source/prior-ledger hash and dirty-path
audits. Existing product and native suites are reused for their unchanged inputs.

automation.suite_command: .venv/bin/python -m pytest -q .phase-loop/runs/PROVIDER-proof-20261004/test_study.py

## Acceptance criteria

- [x] Five provider request paths are checked offline, with the intended model,
      output cap, native authentication and no persisted secrets or raw errors.
- [ ] Each available provider receives the same three tasks in Google-first
      order; unavailable providers stop after one recorded failure. Fresh calls
      stay within the frozen schedule and raw token reservation ceiling.
- [x] Independent reference/negative controls pass; results retain measured
      duration, model identity and token/cost provenance, including unknowns.
- [x] Replay adds no calls; historical study/grant bytes and public source stay
      unchanged, with verified local evidence and all dirty paths classified.
