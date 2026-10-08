# Detailed plan: expanded local Gemma development study

## Task

Continue the authorized roadmap using the existing local Gemma endpoint. The
owner approved local use without a paid-call quota or whole-study time bound.
Finish the 60 prepared development tasks with thinking disabled, then analyze
the observations. Preserve earlier studies, grants and acceptance records.

## Research summary

The actual `ai` endpoint still reports the approved Gemma model and 131,072-token
context. Existing BAML `local_development_completion` and request checks support
thinking-disabled local calls. The old runner has a frozen 24-attempt cap and
two-condition protocol; its ledger must remain untouched. The new corpus has
20 groups and 60 tasks. Its implementation rubric includes input preservation,
which the existing independent grader does not expose in its returned grade.
The underlying restricted runner does expose that observation, so this study
will check it explicitly without changing production code or historical grades.
Offline controls also found that the corpus labels review responses with an old
integer-only contract, while its explicit prompts require varied JSON examples.
The frozen study protocol records this metadata correction: exactly `issues`
and `example`, unique allowed issue labels, and any finite JSON example. The
original corpus bytes stay intact; local validation follows its explicit prompts.

## Changes

- `.phase-loop/runs/GEMMA-development-20261003/study.py`: new private study
  controller importing existing BAML transport, restricted runner and scorers.
  Bind source/corpus/model/runtime/rubric bytes before dispatch. Use a new durable
  ledger with no call quota or whole-study deadline. Run each declared task once,
  persist dispatch before a call, retain uncertain results without redispatch,
  and resume completed observations. Use one request at a time, a 60-second
  hung-request guard and the existing 2,048-output-token condition. Failed or
  truncated answers remain observations. No automatic retry or answer repair.
- `.phase-loop/runs/GEMMA-development-20261003/test_study.py`: meaningful controls
  for restart/uncertain dispatch, protocol drift, more than 24 local observations,
  local BAML request preservation and explicit input-mutation rejection.
- `.phase-loop/runs/GEMMA-development-20261003/**`: private SQLite ledger,
  controlled test records and explicitly owned SSH forward. Do not log raw HTTP,
  credentials, user tasks or server logs. Close the forward at completion.
- `evidence/EXPERIMENT/gemma-development-20261003/**`: protocol, preflight
  controls, purpose-built model outputs, grades, measurements, summary and
  verification. Exposed development data; no promotion or holdout claim.
- `evidence/ROADMAP/latest-study.json`, `plans/manifest.json`,
  `.dev-skills/handoffs/**`: truthful continuation and lifecycle pointers.

Read allowance: preceding owned paths; public BAML/generated SDK, local runner,
restricted grader/scorers and prepared corpus/controls; metadata of `ai`'s
loopback port 8002 `/v1/models`, `/version`, `/metrics`; named existing image
metadata; historical local-study summary/protocol/verification and hash-only old
ledgers/results. No user tasks, private server logs, credentials or sealed data.
Public product source, existing native acceptance and installed packages remain
unchanged. No paid provider, serving change, image pull, publication or activation.

## Documentation impact

The new summary explains the owner's resource decision, the exact operational
guards, output-contract limitations, grouping, unknown prices and next empirical
decisions. Review JSON is locally validated; provider-enforced structured output
is not claimed. The 60 tasks are the study inventory, not a spending quota.

## Dependencies and order

1. Preserve status and source hashes; verify endpoint and existing runtime.
2. Prepare controller/protocol and run offline positive/negative controls.
3. Freeze the protocol and run all 60 tasks through BAML on the local endpoint.
4. Independently grade and analyze; replay without new calls; verify unchanged
   old grants/source and publish only the owned local evidence/handoff.

## Verification

- Existing `tests/verification/test_local_calibration.py` and private
  `test_study.py` through the installed test environment.
- Preflight all 60 reference/negative controls in actual restricted execution;
  include a mutating implementation returning otherwise correct answers.
- Real local study, followed by restart/replay proving no new dispatch.
- Compile/check the private controller; whitespace and input-hash audit; original
  current phase reducers may be reused because public inputs are unchanged.

automation.suite_command: .venv/bin/python -m pytest -q tests/verification/test_local_calibration.py .phase-loop/runs/GEMMA-development-20261003/test_study.py

## Acceptance criteria

- [x] Every inventory task retains its actual completion/failure, output, token
      and timing observations and independent grade; missing values stay unknown.
- [x] Replay makes no extra model call; no old ledger or source binding changes.
- [x] No paid call, whole-study deadline, arbitrary call quota, service change,
      holdout exposure, publication or policy activation occurs.
- [x] Results state empirical limits and the next calibration decision without
      claiming general model superiority or full EXPERIMENT acceptance.
