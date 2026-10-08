# Detailed plan: resume provider proof with the Consiliency service account

## Task

Use the configured `op-account consiliency` wrapper to complete the previously
approved five-provider proof. Current preflight verifies all five named keys.
The owner selected the recommendation and identified this service account.
This replaces the unavailable personal-session path without changing accounts,
vault permissions or stored credentials.

## Changes

- `.phase-loop/runs/PROVIDER-service-proof-20261004/**`: reuse the frozen private
  BAML source, generated SDK and request fixtures from PROVIDER-proof-20261004.
  Add a small controller that binds that source, reads keys through the service
  account wrapper, records failure stages, preflights all keys before dispatch,
  and uses a fresh immutable protocol/ledger. Carry the old $0.374784 conservative
  reservation into the new ledger under the existing $2 guard. Preserve the old
  protocol, observations, ledger and uncertainty; no failed attempt is reset.
- `evidence/EXPERIMENT/provider-service-proof-20261004/**`: filtered live results,
  independent grades, descriptive analysis, access/preflight audit, replay and
  scoped verification. Keep Gemini-first order, three identical tasks for each
  available provider, output limit 2,048, local guard 60 seconds, no retries.
- `evidence/ROADMAP/latest-study.json`: report the replacement's actual outcome
  and retain references to both the completed Gemma study and failed proof.
- `plans/manifest.json`, `.dev-skills/handoffs/**`, skill reflections: lifecycle
  and local closeout. No product source, native verdict, promotion or publication.

Read allowance: named provider items through the service account wrapper; the
wrapper source and service-account configuration metadata; all paths allowlisted
by the preceding plan; its entire private run and public evidence; new owned
paths. Snapshot only hashes of historical studies, SQLite ledgers and grants.
Use this existing task-owned worktree and preserve all inherited changes.

## Documentation impact

Record the corrected authentication path, stage-specific failures, raw token
valuation, measured duration and the limited meaning of three exposed tasks.

## Verification

`.venv/bin/python -m pytest -q .phase-loop/runs/PROVIDER-service-proof-20261004/test_study.py`

`.venv/bin/python .phase-loop/runs/PROVIDER-service-proof-20261004/study.py controls`

`.venv/bin/python .phase-loop/runs/PROVIDER-service-proof-20261004/study.py run`

Offline replay with a dispatch function that raises; zero extra calls, unchanged
ledger/results bytes. Compile, Ruff F, redaction, whitespace and hash/dirty-path
audits. Reuse prior product verification only for its unchanged public inputs.

automation.suite_command: .venv/bin/python -m pytest -q .phase-loop/runs/PROVIDER-service-proof-20261004/test_study.py .phase-loop/runs/PROVIDER-service-proof-20261004/test_followup.py

## Acceptance criteria

- [x] All five service-account key preflights and inherited BAML HTTP fixtures
      pass without saving credential values; failure stages are explicit.
- [x] Execute the fixed Google-first schedule, preserving failures and stopping
      unavailable providers, with no retry and old reservations carried forward.
- [x] Independent grading controls pass and observations retain measured usage,
      latency, model identity and cost provenance, including unknowns.
- [x] Replay adds zero dispatch; public inputs and old grants/studies are unchanged,
      with verified evidence and no non-plan dirty paths.

## Execution amendment: finish four missing tasks

The first service-account run made eleven attempts. Gemini's first request
returned 404 because the explicit base URL omitted `/v1beta`; a Cerebras
documentation attempt timed out at credential retrieval before BAML invocation.
Preserve all eleven observations and the frozen protocol. The remaining four
slots of the fifteen-attempt scope can complete Gemini's three tasks with the
corrected route and the missing Cerebras documentation task.

Add `followup.py`, `test_followup.py`, a separate follow-up SQLite ledger and
`evidence/EXPERIMENT/provider-service-proof-20261004/followup/**` under the already
owned paths. Freeze the corrected URL, exact four-task schedule, inherited source
hashes and prior commitments. Read the two keys before enabling the schedule,
keep them in memory, and send each to its worker through stdin. This prevents
credential retrieval during remote execution and saves repeated vault requests.
The prior ledger and conservative reservations carry forward under the same $2
guard. Do not rerun Together, Groq or completed OpenAI/Cerebras tasks.

Verify the full `/v1beta/models/...:generateContent` path against an actual BAML
HTTP fixture, credential failure/redaction, reference/negative controls already
run, inherited tests and replay of both ledgers. This is a visible correction of
local setup, not an automatic retry or a model fallback. It adopts no new quality
or budget settings.
