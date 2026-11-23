# LEARN interfaces

`jevdrill analyze` consumes strict `AnalysisRequest` JSON. Recording a
`LearningContext` requires the existing scoped task/decision and exact stored
discovery reference. Both the route and analysis settings must explicitly enable
local analysis. Task opt-outs are permanent across import. Analyze and inspect
requests whose settings exclude a path or do not enable local analysis return
`denied`; a record request under such settings stores the context with analysis
off, which opts the task out permanently, and returns `recorded`. User-wide
observations require requesting consent and producer consent; their
task/decision/run/discovery identities are left out of the observation's source
(the source origin is `user_wide_redacted`). For an observation linked to a
discovery, the group conditions still carry the discovery's status, domains and
guidance choices and a digest of the discovery's revisions. Each group lists
digests of its observations. In a user-wide observation, the digest of the
producer's discovery reference, the digest of the discovery's revisions and the
observation's digest are each keyed with a random key that the store keeps and
never exports, together with the requesting project and workspace, so they
differ between requesters and between stores; one requester gets the same values
from one store each time. Evidence stored before the first two were keyed keeps
its earlier values until it is replaced, so each analysis after the change
counts every user-wide observation as new until one of them saves evidence. The
revisions digest was keyed after the other two. That change leaves observation
digests as they were, so the batch trigger counts nothing new because of it, but
each user-wide group linked to a discovery gets a new group identity, once,
because its conditions change; which observations share a group does not change.
Until evidence is next saved, by the batch count or the interval, a changed
objective does not make analysis due again for a requester whose stored evidence
holds such groups, because the stored source digest no longer matches. A store
rebuilt elsewhere from a recovery export has its own key and gives a requester
different values; a copy of the store's file keeps the key. A policy promoted on
earlier evidence is not changed. The discovery's status, domains and guidance
choices are not keyed, nor are the group's other conditions (context fields,
configuration digests, policy revision, model) or its measurements: they are the
same for every requester and store, so they can still link one producer's groups
across requesters, and a holder of the producer's discovery result can match its
status and guidance choices. Keying protects only values a requester has not
already received: one holding output from before the revisions digest was keyed
can pair its old and new values through the unchanged observation digests.
Within one requester's view, a keyed value still links every observation that
shares it, for example the observations of one producer's discoveries made with
the same constraints, catalog and settings.

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
`python -I -m jevdrill.cli`; `-I` keeps the job's working directory, `PYTHON*`
variables and the user site directory off the import path
(Consiliency/jevdrill#52). An item that cannot be verified when it is archived
(its digest no longer matches, or its existing archive no longer decrypts or
matches) is reported in a persistent notice naming its identity, not its
content; it is left as it is, the run goes on to the others, and a later run
tries it again. Storage and file-system errors, including a missing file, still
stop the run. A replaced archive key makes every item with an existing archive
fail this way. A run processes up to `max_items` items after a cursor that
survives restarts, in identity order, and the run that reaches the last item
ends the pass. A pass reaches every item present when it starts within
`ceil(N / max_items)` completed runs, where `N` counts every item in scope
during the pass, archives it makes included; an item that appears during a pass,
such as an archive the pass makes, is reached by the end of the next pass. So,
with a fixed set of items, every item is reached within
`ceil(N / max_items) + 1` completed runs from any point, however many fail
(Consiliency/jevdrill#45).

When a run completes, the application passes the stored objectives of the last
analysis to a new analysis, which applies the credential check to them. If
stored text now fails that check, the command answers `invalid_input` although
the maintenance work is done and committed, and each later completed run does
the same until that evidence is replaced (Consiliency/jevdrill#58).

Active raw task/output/context content is prompted at 30 days, archived after
seven additional days, and expires one year after successful archival with
seven-day advance notice. Content restored and archived again before its first
archive expires keeps that archive and its expiry, and the expiry notice says so
(Consiliency/jevdrill#46). Content restored and archived again after its first
archive has expired gets a new archive, which expires one year after that
archival, whatever the order and timing of runs (Consiliency/jevdrill#125).
Measurements persist until explicit deletion. Each
is a number, or a reason from a fixed list when the value is unknown, with a
metric name, version, method, unit and parent metric that the reporting host
chooses; that text is checked only for credential-like material. Only
authenticated archives may replace active content, after durable-byte
verification. Missing/locked/failed OS keys keep content pending with persistent
notices. Clock rollback pauses retention. Supported stores are macOS Keychain,
Windows Credential Locker and Linux Secret Service; no plaintext fallback or
automatic key provisioning exists.

`jevdrill recovery` consumes `RecoveryRequest`: export/backup/import require an
explicit portable Fernet key; restore requires an archive identity and
configured OS archive key. An export or backup is not metadata only. It carries
the scope's routing decisions, reports, learning contexts, task/objective
deletion and learning opt-out records and metadata-only discovery linkage, and
also its retained raw task, output and context content in full. Archived content
is decrypted with the OS archive key to go into the bundle, so an export then
needs that key as well. The bundle is encrypted with the portable key. Text that
the credential check did not detect is exported with the rest (see [the
credential check](sanitization-contract.md)). Discovery instructions, a
discovery request's own retained content (its objective, context and
attachments) with the archives of it, retired content, the content of deleted
tasks and key-store credentials are excluded. The retained content of a task
whose route is linked to a discovery is not excluded: it is exported like any
other task's. Import validates integrity and conflicts transactionally, merges
permanent deletion/opt-out before restoring sources, and leaves policy
validation stale. Recovered discovery metadata supports analysis linkage; it
does not reconstruct planning instructions or authorize a fresh discovery
replay. Existing tombstones remain authoritative. Import and restore write the
saved text back to local storage as it was saved: it is not passed through the
credential check, and it is written back even if raw retention is now off.
