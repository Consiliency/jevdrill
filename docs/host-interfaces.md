# HOST interfaces

The host calls installed `discover` before its ordinary planning path constructs
tasks. Successful `DiscoveryResult` instructions are transient planning input;
Drill does not create task lists. Each bound task supplies `DiscoveryRouteInputs`
version 2 through a trusted host callback, preserving the exact stored reference.
Route-v1 remains available for unbound compatibility tasks.

`JevDrillAdapter.discover_objective(inputs, *, started_at=None)` validates the
strict result. Only selected_guidance and no_optional_guidance permit linked
task launch. Other statuses expose remediation. The host ledger retains only
project/workspace/producer and objective/discovery/task/decision/run identities
and trace digest. It rechecks stored discovery and current authorized revisions
before launch. Objective deletion commits a permanent cross-producer tombstone
before transport; task reports retain their separate lifecycle.

`NoticeRequest {schema_version: "1", scope: CommandScope}` and
`NoticeInbox {schema_version: "1", notices: LocalNotice[]}` freeze read-only
`StoragePort.load_notices(scope)`, `Application.notices(payload)` and stdin
`jevdrill --storage PATH notices`. Scope is project/workspace. Repeated reads do
not acknowledge notices. Fresh decisions snapshot notices; retry/replay remain
immutable. Discover connections query notices with operation route in
CommandScope; this changes no project/workspace authority.

Each logical discover/route call and its notice query share a spawn-inclusive
five-second budget and 1,000,000-byte bounds. Planning/execution have separate
host budgets. Callbacks retain configured/runtime capabilities, operator model
overrides, worktree/delegation authority and recursion bypass. Selected identities
are validated before apply; host retain/decline remains a separate preference.
Optional guidance is injected once per fresh task prompt and deactivated after
execution; parent prompts remain immutable.

One ReportQueue serves hooks and explicit reports: 16 MiB payload, 10,000 rows,
1 MiB each, seven days, native restrictive permissions, bounded backoff. Sanitize
before writes. Removal requires matching event ID, accepted/duplicate and
durable=true. Rejection, conflict, corruption, expiry and overflow remain visible.
Companion schemas/fixtures and native receipts bind exact content digests.
