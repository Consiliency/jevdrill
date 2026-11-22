# LEARN interfaces

`jevdrill analyze` consumes strict `AnalysisRequest` JSON. Recording a
`LearningContext` requires the existing scoped task/decision and exact stored
discovery reference. Both the route and analysis settings must explicitly enable
local analysis. Task opt-outs are permanent across import; excluded analysis
requests return denied. User-wide observations require requesting consent and
producer consent; their task/decision/run/discovery identities are left out
(the source origin is `user_wide_redacted`).

Comparable groups retain task family/group, environment/isolation, actual
evaluator/rubric revisions, source measurement definitions and selected/applied
configuration. Recorded discovery identity, domain metadata, choices and
revisions define an additional boundary, including no-guidance outcomes.
`ObservationSource` exposes local discovery/task/decision/run linkage. Reports
determine completed/failed/canceled/incomplete status, substitutions and
retain/decline preferences independently of measured acceptance and unknown
usage. Substitution does not establish the substituted configuration's details.
Effective lifecycle reports, including terminal-only applied plan IDs and
corrections, determine the applied identity separately for each run. Its reason
is `reported_selected_plan`, `different_plan` or `not_reported`; the latter two
retain unknown configuration details.

`minimum_batch` and `interval_seconds` are operational triggers. Each derived
revision rechecks the observation digest under write admission. Objective
reassessment retains source measurements and previous objective versions.
Assessment remains insufficient evidence for causal benefit, whole-skill or
cross-domain claims. No route, navigation, experiment or promotion action is
performed. Model-assisted analysis is unavailable; enabling its setting cannot
launch it.

`jevdrill maintenance` consumes `MaintenanceRequest`. `max_items` bounds each
resumable batch; process-owned file locks prevent overlap. Pause/cancel and the
host's interactive flag are rechecked between items. `schedule` requires an
existing absolute `request_path` containing a scoped run request. Generated
systemd, launchd or Task Scheduler configuration calls the installed interpreter
with `--request-file PATH maintenance`; no configuration is installed/enabled.
Paths with control characters are refused. The generated command is
`python -m jevdrill.cli`, and under `-m` Python puts the job's working directory
first on its import path (Consiliency/jevdrill#52).

When a run completes, the application passes the stored objectives of the last
analysis to a new analysis, which applies the credential check to them. If
stored text now fails that check, for example after a backup import, the command
answers `invalid_input` although the maintenance work is done and committed, and
each later scheduled run does the same until that evidence is replaced
(Consiliency/jevdrill#58).

Active raw task/output/context content is prompted at 30 days, archived after
seven additional days, and expires one year after successful archival with
seven-day advance notice. Measurements persist until explicit deletion; they
hold no raw task, output or context content.
Only authenticated archives may replace active content, after durable-byte
verification. Missing/locked/failed OS keys keep content pending with persistent
notices. Clock rollback pauses retention. Supported stores are macOS Keychain,
Windows Credential Locker and Linux Secret Service; no plaintext fallback or
automatic key provisioning exists.

`jevdrill recovery` consumes `RecoveryRequest`: export/backup/import require an
explicit portable Fernet key; restore requires an archive identity and configured
OS archive key. Export includes metadata-only discovery linkage and independent
task/objective deletion and learning opt-out records. Discovery instructions and
key-store credentials are excluded. Import validates integrity and conflicts
transactionally, merges permanent deletion/opt-out before restoring sources,
and leaves policy validation stale. Recovered discovery metadata supports
analysis linkage; it does not reconstruct planning instructions or authorize a
fresh discovery replay. Existing tombstones remain authoritative. Import and
restore write the saved text back to local storage as it was saved: it is not
passed through the credential check, and it is written back even if raw
retention is now off (see [the credential check](sanitization-contract.md)).
