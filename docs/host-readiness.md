# HOST readiness

The current verdict is `evidence/HOST/verification.json`. HOST requires all four
EC-HOST criteria, IF-0-HOST-1, inherited ROUTE regressions and matching native
Linux/macOS/Windows Python 3.13 receipts. Missing companion configuration fails
closed. Source/schema/fixture hashes, executed test identities and entered CLI,
discovery, planner, task, launch and acknowledgment records bind each receipt.
Historical ROUTE evidence remains unchanged.

The separately owned agent-harness companion supports explicit, default-disabled
serial integration. Installed discovery returns transient guidance to a trusted
host planning callback; the normal plan IR constructs independent task lanes.
Only selected_guidance/no_optional_guidance may bind route-v2 tasks. Each task
has independent inventory/constraints and route budget. Explicit host model
overrides and retain/decline preferences remain authoritative.

Objective binding stores opaque project/workspace/producer/objective/discovery,
trace digest and task/decision/run linkage. A forged or deleted reference and
changed authorized catalog/revision block launch. Objective deletion is permanent
across producers; its local tombstone commits before transport and survives lost
responses/restart. Task report deletion remains independent. Lifecycle locking
serializes final launch against deletion: already-running work completes before
a waiting deletion can commit; lock acquisition has a five-second bound and a
caller may retry after a lock timeout. No claim of stopping running work follows.

One private durable queue serves hooks and explicit reports, with 16 MiB payload,
10,000 rows, 1 MiB each and seven-day retention. Sanitization precedes database
and journal writes. Only matching durable accepted/duplicate acknowledgments
remove events. Failed delivery preserves executor outcomes. Rejection/conflict,
corruption, expiry and overflow remain visible. Every report connection fetches
notices; repeated notice reads do not acknowledge or mutate immutable decisions.

Guidance is confined to fresh task prompts. Retry unwraps a prior injected prompt
to its immutable base; unrelated tasks retain their own prompt state. Required
guidance is preserved, optional revisions are validated and injected once, and
cleanup emits deactivation. Requested token/spending ceilings require verified
whole-run enforcement; estimates/unknown prices never become hard limits.

```sh
BAML_CLI=/path/to/baml-cli uv run python scripts/verify_host_phase.py --local-only --agent-harness PATH
uv run python scripts/verify_host_phase.py --reduce-only --agent-harness PATH
```

The companion environment remains separate from JEV's BAML bridge 0.20.1.
Native Windows uses its installed interpreter with `-m jevdrill.cli`. macOS
ordinary execution remains local; leased startup retains the JD-084 configured
Linux-worker rejection. No runtime install, publication, security-policy change,
ratified review or adoption occurs in this phase.

The native command matrix runs adapter, queue, discovery and existing launcher
regressions on every host. Codex input/usage observer regression suites run on
Linux, the observer's supported platform. Darwin and Windows enter the production
capture path and require explicit disabled/unknown capture provenance; absent
observer suites on those hosts do not establish provider usage or receipt.
Each receipt checks hashes of the modules imported by the companion interpreter.

The frozen development/validation protocol uses predetermined synthetic programs,
independent all-required artifact checks, paired feasible baselines and entered
damaged/privacy/split controls. Receipts separate objective checks, unknown model
judgments and host preferences; artifacts are removed before evidence retention.
These establish conformance, not model quality or guidance effectiveness. Live
latency, empirical floors, gains and promotion remain insufficient evidence
pending Q-12/Q-13, authorization and independent datasets. Holdouts remain closed.
Replan LEARN before consuming the linked reports and objective lifecycle.
