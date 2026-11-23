"""LEARN SL-3: LEARN-side controls, each entered through `Application`.

These test `main` as it is. Stores, keys and evidence are synthetic; no provider is
called and nothing is spent.

Keys and clocks. `Application.maintain` and `Application.recover` build
`Maintenance(storage)` with its default key provider (`maintenance.py:28`, the OS key
store) and the wall clock. The `synthetic` fixture replaces both defaults for the test's
duration with a synthetic Fernet key and an injected clock, injects the same clock into
analysis (`application.py:1274`), and makes the key-store child process
(`integrations/archive.py:50`) fail the test if anything reaches it. Policy lifecycles
get an injected clock too. Artifact bytes are written and compared as bytes.

Citations: `docs/sanitization-contract.md` lines 30 and 31; Consiliency/jevdrill#53 and
Consiliency/jevdrill#58.
"""

import copy
import itertools
import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet

from jevdrill.application import Application
from jevdrill.context import redact
from jevdrill.contracts import ContractError, canonical_digest
from jevdrill.discovery import reference
from jevdrill.integrations import archive
from jevdrill.integrations.archive import decrypt_archive
from jevdrill.maintenance import DAY, Maintenance
from jevdrill.routing import candidate_fingerprint
from jevdrill.storage import SQLiteStorage
from tests.experiments.test_execution import seed_task
from tests.promotion.test_lifecycle import Evidence

FIXTURES = Path(__file__).parents[1] / "contracts" / "fixtures"
START = 1_000_000.0
GROUP = "learning-limits"
# Prepared candidate ids carry the digest of their optional guidance (none here).
SUFFIX = canonical_digest([])[:12]
# Text a new submission is refused for: a listed name followed by a sign, a bearer token
# at the start of a line, and the first line of a PEM private key (contract lines 9-12).
REFUSED = (
    "DB_PASSWORD=synthetic-not-a-secret",
    "Bearer synthetic.not.a.token",
    "-----BEGIN PRIVATE KEY-----",
)
# Bytes no text handling would keep: every line ending, NUL and invalid UTF-8.
AWKWARD = b"first\r\nsecond\rthird\n\x00\xff\xfe" + bytes(range(256)) + b"\r\n"
# The raw kinds that raw retention governs.
RAW = ("raw_task", "raw_output")
# Valid UTF-8 with every line ending, so a step that decodes text first is tried too.
TEXT = "first\r\nsecond\rthird\nnon-ASCII: \u00e9\u00f8\u2713\r\n".encode()
# The same text after a UTF-8 byte-order mark.
BOM = b"\xef\xbb\xbf" + TEXT


class NoProvider:
    """A judgment port that fails the test if it is called: nothing here asks a provider."""

    model_revision = "jev-latest"

    def judge(self, *args):
        pytest.fail("a route judgment was requested")

    def observe_option(self, *args):
        pytest.fail("a discovery judgment was requested")


class Observer:
    """A synthetic discovery port: an option is supported unless it is a resource whose
    description does not mention the objective. Nothing asks a provider."""

    model_revision = "jev-latest"

    def observe_option(self, task, offered, question_digest, option_id, deadline):
        option = json.loads(offered)
        return {
            "schema_version": "1",
            "function_revision": "ObserveDiscoveryOption-v1",
            "model_revision": "jev-latest",
            "question_digest": question_digest,
            "judgments": {
                option_id: option["level"] != "resource"
                or json.loads(task)["objective"] in (option["description"] or "")
            },
            "measurements": [],
        }


@pytest.fixture
def synthetic(monkeypatch):
    ticks = itertools.count()
    clock = SimpleNamespace(
        now=START,
        key=Fernet.generate_key(),
        # Policy lifecycles: one second later at each reading, never earlier, in every store.
        instant=lambda: datetime(2026, 1, 2, tzinfo=UTC) + timedelta(seconds=next(ticks)),
    )

    def key_store(*args, **kwargs):
        pytest.fail("the OS key store was reached")

    monkeypatch.setattr(
        archive,
        "subprocess",
        SimpleNamespace(
            run=key_store, DEVNULL=subprocess.DEVNULL, TimeoutExpired=subprocess.TimeoutExpired
        ),
    )
    monkeypatch.setattr(
        Maintenance.__init__, "__defaults__", (lambda _: clock.key, lambda: clock.now)
    )
    monkeypatch.setattr("jevdrill.application.time", lambda: clock.now)
    return clock


def inputs():
    """The discovery and route fixtures in one scope, with no catalog resource."""
    discovery = json.loads((FIXTURES / "discovery.json").read_text(encoding="utf-8"))[0]["payload"]
    discovery["catalog"]["resources"] = []
    discovery["descriptions"] = []
    route = json.loads((FIXTURES / "route-application.json").read_text(encoding="utf-8"))[0][
        "payload"
    ]
    request = route["request"]
    request["active_guidance"] = []
    cheaper = route["inventory"]["candidates"][0]
    cheaper["guidance_options"] = []
    # A dearer candidate the router does not choose unless a policy orders it first.
    preferred = copy.deepcopy(cheaper)
    preferred.update(
        candidate_id="preferred", model_id="preferred", resolved_model_revision="preferred-v1"
    )
    preferred["rates"].update(input_rate="0.01", output_rate="0.01")
    route["inventory"]["candidates"].append(preferred)
    route["settings_layers"] = [{"source": "request", "values": {"local_analysis_enabled": True}}]
    for key in ("project_id", "workspace_id", "harness_id"):
        request["envelope"][key] = discovery["envelope"][key]
    request["hard_constraints"] = discovery["hard_constraints"]
    route["catalog"] = discovery["catalog"]
    envelope = request["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "route",
    }
    return discovery, route, scope


def application(path, scope, synthetic, policy=False, observer=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {}
    if policy:
        authority = {
            "schema_version": "1",
            "authorization_revision": "owner",
            "scope": scope,
            "enabled": True,
            "allowed_task_groups": [GROUP],
            "allowed_policy_revisions": ["one", "two"],
            "max_routes": 1000,
            "rollout_basis_points": 10000,
            "expires_at": "2099-01-01T00:00:00Z",
        }
        kwargs = {
            "policy_authority": lambda _: authority,
            "policy_evidence": Evidence(),
            "policy_task_group": lambda request: GROUP,
        }
    app = Application(
        SQLiteStorage(path),
        judgments=NoProvider(),
        discovery_judgments=Observer() if observer else NoProvider(),
        **kwargs,
    )
    app.policy_lifecycle.clock = synthetic.instant
    return app


def discover(app, discovery, key):
    payload = copy.deepcopy(discovery)
    payload["envelope"].update(request_id=key, idempotency_key=key)
    result = app.discover(payload)
    app.storage.deadline = None
    return result


def linkage(result):
    return {k: result["details"][k] for k in ("discovery_id", "work_objective_id", "trace_digest")}


def route_task(app, route, task, request, link=None, retain_raw=None, text=None):
    payload = copy.deepcopy(route)
    payload["request"]["task_id"] = task
    payload["request"]["envelope"].update(request_id=request, idempotency_key=request)
    if text is not None:
        payload["request"]["task_representation"] = text
    if retain_raw is not None:
        payload["settings_layers"][0]["values"]["retain_raw_tasks"] = retain_raw
    try:
        return app.route(
            payload
            if link is None
            else {"schema_version": "2", "route_inputs": payload, "discovery_ref": link}
        )
    finally:
        app.storage.deadline = None


def context_for(decision, link=None, **changes):
    return {
        "task_id": decision["details"]["task_id"],
        "routing_decision_id": decision["details"]["routing_decision_id"],
        "discovery_ref": link,
        "task_family": "implementation",
        "task_group": "parser",
        "environment_revision": "native-v1",
        "isolation_revision": "temp-v1",
        "evaluator_ref": "checks-v1",
        "rubric_revision": "v1",
        "local_analysis_enabled": True,
        "share_user_wide": False,
    } | changes


def analysis(scope, action="analyze", context=None, objectives=()):
    return {
        "schema_version": "1",
        "scope": scope,
        "action": action,
        "context": context,
        "objectives": list(objectives),
        "minimum_batch": 1,
        "interval_seconds": 60,
        "include_user_wide": False,
        "settings_layers": [{"source": "request", "values": {"local_analysis_enabled": True}}],
    }


def record(app, scope, decision, link=None):
    context = context_for(decision, link)
    assert app.analyze(analysis(scope, "record", context))["status"] == "recorded"
    return context


def maintenance(scope):
    return {
        "schema_version": "1",
        "scope": scope,
        "action": "run",
        "interactive_busy": False,
        "max_items": 10,
        "archive_retention_days": 365,
        "request_path": None,
    }


def recovery(scope, action, key=None, bundle=None, artifact=None):
    return {
        "schema_version": "1",
        "scope": scope,
        "action": action,
        "artifact_id": artifact,
        "encrypted_bundle": bundle,
        "recovery_key": None if key is None else key.decode(),
    }


def stage(app, scope, task, content, kind="raw_task", created=START):
    """Content saved in the store at `created`, as an earlier version or import saved it."""
    return app.storage.stage_artifact(
        scope,
        task,
        content,
        kind=kind,
        retention="active",
        encryption="none",
        retain_raw_tasks=True,
        retain_raw_outputs=True,
        created_at=created,
    )


def archive_item(app, scope, synthetic, *identities):
    """Two maintenance runs through `Application`: the 30-day prompt, then the archive.
    Returns each item's archive identity and archival time, in order."""
    synthetic.now = START + 30 * DAY
    assert app.maintain(maintenance(scope))["processed"] == len(identities)
    synthetic.now += 7 * DAY
    assert app.maintain(maintenance(scope))["processed"] == len(identities)
    directory = app.storage._artifact_directory(app.storage._task_scope(scope))
    archives = []
    for identity in identities:
        with app.storage._connect() as c:
            archives.append(
                c.execute(
                    "SELECT a.artifact_id,l.archived FROM artifacts a JOIN artifact_lifecycle l ON a.scope=l.scope AND a.artifact_id=l.artifact_id WHERE a.kind='archive' AND l.source_id=?",
                    (identity,),
                ).fetchone()
            )
        assert not (directory / identity).exists()
    return archives if len(archives) > 1 else archives[0]


def active_bytes(app, scope, task, kind):
    """The bytes on disk of each active artifact of `kind` held for `task`."""
    pair = app.storage._task_scope(scope)
    with app.storage._connect() as c:
        identities = [
            row[0]
            for row in c.execute(
                "SELECT artifact_id FROM artifacts WHERE scope=? AND task=? AND kind=? AND retention='active'",
                (pair, task, kind),
            )
        ]
    return [(app.storage._artifact_directory(pair) / i).read_bytes() for i in identities]


def policy_tables(c):
    # The name filter leaves out `task_learning_policy` on purpose: it is the learning
    # opt-out, written by recording a context, not a policy record.
    return [
        row[0]
        for row in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'policy%' ORDER BY name"
        )
    ]


def policy_rows(app):
    """Every row of every policy table, as stored."""
    with app.storage._connect() as c:
        return {t: sorted(map(repr, c.execute(f"SELECT * FROM {t}"))) for t in policy_tables(c)}


def watch_policy_writes(app):
    """From here on, log every insert, update and delete on a policy table, even one that
    leaves the rows as they were. The log is a table no policy query reads."""
    with app.storage._connect(True) as c:
        c.execute("CREATE TABLE audit_policy_writes (statement TEXT NOT NULL)")
        for table in policy_tables(c):
            for operation in ("INSERT", "UPDATE", "DELETE"):
                c.execute(
                    f"CREATE TRIGGER audit_{table}_{operation.lower()} AFTER {operation} ON {table} "
                    f"BEGIN INSERT INTO audit_policy_writes VALUES ('{operation} {table}'); END"
                )


def policy_writes(app):
    with app.storage._connect() as c:
        return [row[0] for row in c.execute("SELECT statement FROM audit_policy_writes")]


def definition(revision, baseline, route, tasks):
    cheaper, preferred = route["inventory"]["candidates"]
    return {
        "schema_version": "1",
        "policy_revision": revision,
        "baseline_policy_revision": baseline,
        "task_group": GROUP,
        "objective": route["request"]["optimization_objective"],
        "candidate_order": [
            {
                "candidate_id": f"{candidate['candidate_id']}:{SUFFIX}",
                "candidate_fingerprint": candidate_fingerprint(candidate),
            }
            for candidate in (preferred, cheaper)
        ],
        "calibration": {
            "schema_version": "1",
            "calibration_revision": "fixture-only",
            "task_family": "review",
            "evaluator_ref": "fixture",
            "rubric_revision": "fixture",
            "dataset_revision": "fixture",
            "calibration_source": "synthetic-control",
            "frozen_at": "2026-01-01T00:00:00Z",
            "critical_requirements": ["authorization"],
            "quality_floor": 0.7,
            "maximum_quality_loss": 0.4,
            "minimum_pairs": 100,
            "confidence": 0.95,
        },
        "cases": [
            {
                "case_id": str(i),
                "related_group": f"{revision}-{i}",
                "task_id": task,
                "split": "policy_holdout" if i < 100 else "policy_regression",
            }
            for i, task in enumerate(tasks)
        ],
        "objective_value_ceiling": 1.0,
        "minimum_improvement": 0.1,
    }


def promote(app, scope, policy):
    """Register, evaluate on synthetic evidence and promote, through `Application`."""
    request = {
        "schema_version": "1",
        "scope": scope,
        "policy_revision": policy["policy_revision"],
        "action": "register",
        "definition": policy,
    }
    assert app.manage_policy(request)["status"] == "recorded"
    for action in ("evaluate", "promote"):
        result = app.manage_policy(request | {"action": action, "definition": None})
        assert result["status"] == "recorded", result
    assert result["record"]["policy_status"] == "active"
    return request


def inspect_policy(app, request):
    return app.manage_policy(request | {"action": "inspect", "definition": None})["record"]


def learning_store(path, synthetic):
    """A store with an active promoted policy, an archived item, two analysed tasks routed
    under the policy (one linked to a discovery), saved evidence without outcomes, then
    two more tasks with reported outcomes, one succeeded and one failed."""
    discovery, route, scope = inputs()
    # Two attempts, so a failed run may be retried (the discovery and the route share
    # these constraints).
    route["request"]["hard_constraints"]["max_attempts"] = 2
    app = application(path, scope, synthetic, policy=True, observer=True)
    tasks = [str(uuid4()) for _ in range(200)]
    for task in tasks:
        seed_task(app.storage, scope, task)
    promote(app, scope, definition("one", "execution-ceilings-v1", route, tasks))
    _, archived = archive_item(
        app, scope, synthetic, stage(app, scope, str(uuid4()), b"synthetic task")
    )
    link = linkage(discover(app, discovery, str(uuid4())))
    first = route_task(app, route, str(uuid4()), str(uuid4()), link)
    assert any(d["code"] == "learned_policy_ordering" for d in first["details"]["diagnostics"])
    record(app, scope, first, link)
    record(app, scope, route_task(app, route, str(uuid4()), str(uuid4())))
    objective = route["request"]["optimization_objective"]
    synthetic.now += 1
    assert app.analyze(analysis(scope, objectives=[objective]))["status"] == "updated"
    assert outcome_groups(app, scope) == []
    # After the saved evidence: two more tasks routed under the policy, one run that
    # succeeded with a measurement and one that failed its checks, so the next evidence
    # carries both kinds of outcome for the policy's revision, and metrics.
    runs = {}
    for succeeded in (True, False):
        task, request = str(uuid4()), str(uuid4())
        later = route_task(app, route, task, request)
        assert later["details"]["versions"]["policy_revision"] == "one"
        record(app, scope, later)
        runs[succeeded] = (task, request, later, report_outcome(app, route, later, succeeded))
    return SimpleNamespace(
        app=app,
        discovery=discovery,
        route=route,
        scope=scope,
        objective=objective,
        archived=archived,
        failed=runs[False],
    )


def report_outcome(app, route, decision, succeeded=True):
    """A run of `decision` reported through `Application`: its plan applied, its checks
    passed and a known measurement, then completed; or, if not `succeeded`, its checks
    failed, then failed."""
    run = str(uuid4())
    payloads = [
        {
            "kind": "lifecycle",
            "event_type": "plan_applied",
            "applied_plan_id": decision["execution_plan"]["execution_plan_id"],
            "reason": None,
        },
        {
            "kind": "evaluation",
            "evaluator_ref": "checks-v1",
            "rubric_revision": "v1",
            "check_results": {"tests": succeeded},
            "measurements": [],
        },
        {
            "kind": "usage",
            "measurements": [
                {
                    "metric_id": "input_tokens",
                    "metric_version": "v1",
                    "measurement_value": {"kind": "known", "value": 12, "unit": "tokens"},
                    "source": "host",
                    "method": "direct-v1",
                    "scope": "run",
                    "counting_semantics": "disjoint",
                    "parent_metric_id": None,
                }
            ],
        },
        {
            "kind": "lifecycle",
            "event_type": "completed" if succeeded else "failed",
            "applied_plan_id": None,
            "reason": None if succeeded else "measured failure",
        },
    ]
    for sequence, payload in enumerate(payloads, 1):
        identity = str(uuid4())
        envelope = dict(
            route["request"]["envelope"],
            operation="report",
            request_id=identity,
            idempotency_key=identity,
        )
        event = {
            "schema_version": "1",
            "event_id": identity,
            "task_id": decision["details"]["task_id"],
            "routing_decision_id": decision["details"]["routing_decision_id"],
            "execution_run_id": run,
            "source_id": "synthetic-host",
            "source_sequence": sequence,
            "occurred_at": "2026-10-09T00:00:00Z",
            "supersedes_event_id": None,
            "payload": payload,
        }
        assert app.report({"envelope": envelope, "event": event})["status"] == "accepted"
    return run


def outcome_groups(app, scope):
    """The latest evidence's groups for policy "one" that hold a completed, accepted run,
    a failed and rejected run, and a metric."""
    return [
        g
        for g in app.storage.latest_evidence(scope)[1]["groups"]
        if g["conditions"]["policy_revision"] == "one"
        and g["completed_count"]
        and g["accepted_count"]
        and g["failed_count"]
        and g["rejected_count"]
        and g["metrics"]
    ]


def evidence_revision(app, scope):
    return app.storage.latest_evidence(scope)[1]["evidence_revision"]


def test_analysis_writes_no_policy_record(tmp_path, synthetic):
    """EC-LEARN-1 "Under existing policy" (D new, SL-3)."""
    store = learning_store(tmp_path / "route.db", synthetic)
    app, scope = store.app, store.scope
    decision = route_task(app, store.route, str(uuid4()), str(uuid4()))
    before = policy_rows(app)
    assert len(before) == 7 and before["policy_records"] and before["policy_uses"]
    watch_policy_writes(app)
    revision = evidence_revision(app, scope)
    steps = [
        analysis(scope, "record", context_for(decision)),
        analysis(scope, objectives=[store.objective]),
        analysis(scope, objectives=[dict(store.objective, version="reclassified-v2")]),
        # Nothing new and within the interval: not due.
        analysis(scope, objectives=[dict(store.objective, version="reclassified-v2")]),
        # The same, reading user-wide evidence as well.
        dict(
            analysis(scope, objectives=[dict(store.objective, version="reclassified-v2")]),
            include_user_wide=True,
        ),
        analysis(scope, "inspect"),
    ]
    statuses = []
    for step in steps:
        synthetic.now += 1
        statuses.append(app.analyze(step)["status"])
        assert policy_writes(app) == []
        assert policy_rows(app) == before
    assert statuses == ["recorded", "updated", "updated", "not_due", "not_due", "inspected"]
    assert evidence_revision(app, scope) != revision


@pytest.mark.parametrize("run", ["retire", "retire_and_prompt"])
def test_maintenance_follow_up_analysis_writes_no_policy_record(tmp_path, synthetic, run):
    """EC-LEARN-1 "Under existing policy" (D new, SL-3), for the follow-up analysis. The
    run retires an expired archive and writes no notice (`retire`), or also writes an
    archive prompt for a 30-day-old item (`retire_and_prompt`)."""
    store = learning_store(tmp_path / "route.db", synthetic)
    app, scope = store.app, store.scope
    synthetic.now = store.archived + 366 * DAY
    if run == "retire_and_prompt":
        stage(app, scope, str(uuid4()), b"synthetic task", created=synthetic.now - 30 * DAY)
    before = policy_rows(app)
    assert len(before) == 7 and before["policy_records"] and before["policy_uses"]
    watch_policy_writes(app)
    revision = evidence_revision(app, scope)
    result = app.maintain(maintenance(scope))
    prompted = run == "retire_and_prompt"
    assert result["status"] == "completed" and result["processed"] == 1 + prompted
    assert [n["kind"] for n in result["notices"]] == ["archive_prompt"] * prompted
    # The follow-up ran over the prior evidence and saved new evidence.
    assert evidence_revision(app, scope) != revision
    assert policy_writes(app) == []
    assert policy_rows(app) == before


@pytest.mark.parametrize("learning", ["analysis", "maintenance"])
def test_identical_inputs_give_the_same_later_discovery_and_route(
    tmp_path, synthetic, monkeypatch, learning
):
    """EC-LEARN-5 "Policy writes limited to authorized candidate ordering; no learned
    navigation change" (D new, SL-3).

    The store is copied before the learning step; the learning runs in one copy. Every
    field of each later result is compared, none left out. The inputs, the request
    identities among them, are the same in both copies, and the one random value on the
    path, a discovery's identity (`storage.py:1635`), is pinned to the same sequence in
    both, so the identities and the trace digests that cover them are compared as well.
    The later requests are: a discovery with no catalog resource and a route linked to it;
    an unlinked route; a discovery that selects guidance and a route linked to it; the
    failed run's route sent again; a retry of that failed run; and the guided discovery
    sent again.
    """
    original = tmp_path / "original"
    store = learning_store(original / "route.db", synthetic)
    scope = store.scope
    shutil.copytree(original, tmp_path / "before")
    shutil.copytree(original, tmp_path / "after")
    before = application(
        tmp_path / "before" / "route.db", scope, synthetic, policy=True, observer=True
    )
    after = application(
        tmp_path / "after" / "route.db", scope, synthetic, policy=True, observer=True
    )
    revision = evidence_revision(after, scope)
    if learning == "analysis":
        synthetic.now += 1
        assert after.analyze(analysis(scope, objectives=[store.objective]))["status"] == "updated"
    else:
        synthetic.now = store.archived + 366 * DAY
        result = after.maintain(maintenance(scope))
        assert result["status"] == "completed" and result["processed"] == 1
    assert evidence_revision(after, scope) != revision
    assert evidence_revision(before, scope) == revision
    # The learning step's evidence carries both outcomes and a metric for the policy's
    # revision; the other copy's does not.
    assert outcome_groups(after, scope) and outcome_groups(before, scope) == []
    # The later requests. A discovery over the whole catalog selects guidance, and a
    # route is linked to it; the failed run's route is sent again (the stored decision
    # comes back) and retried under a retry context.
    guided = json.loads((FIXTURES / "discovery.json").read_text(encoding="utf-8"))[0]["payload"]
    guided["hard_constraints"] = store.route["request"]["hard_constraints"]
    guided_route = copy.deepcopy(store.route)
    guided_route["catalog"] = guided["catalog"]
    guided_task = "00000000-0000-4000-8000-000000000105"
    guided_route["inventory"]["candidates"][0]["guidance_options"] = [
        reference(row)
        | {
            "role": "optional-" + str(number),
            "admission": row["admission"],
            "authority": "synthetic-admission",
            "task_id": guided_task,
            "token_count": None,
        }
        for number, row in enumerate(guided["catalog"]["resources"])
    ]
    failed_task, failed_request, failed, failed_run = store.failed
    retry = copy.deepcopy(store.route)
    retry["request"]["retry_context"] = {
        "prior_routing_decision_id": failed["details"]["routing_decision_id"],
        "prior_execution_run_id": failed_run,
        "failure_class": "quality",
        "failure_summary": "synthetic checks failed",
        "remaining_attempts": 1,
        "remaining_time_ms": 5000,
        "remaining_spend": None,
    }
    for candidate in retry["inventory"]["candidates"]:
        candidate["addresses_failures"] = ["quality"]
    later = {}
    for name, app in (("before", before), ("after", after)):
        # The one random value on the path, pinned to the same sequence in both copies.
        identities = itertools.count(7)
        monkeypatch.setattr(
            "jevdrill.storage.uuid4", lambda identities=identities: UUID(int=next(identities))
        )
        found = discover(app, store.discovery, "00000000-0000-4000-8000-000000000100")
        selected = discover(app, guided, "00000000-0000-4000-8000-000000000106")
        later[name] = [
            found,
            route_task(
                app,
                store.route,
                "00000000-0000-4000-8000-000000000101",
                "00000000-0000-4000-8000-000000000102",
                linkage(found),
            ),
            route_task(
                app,
                store.route,
                "00000000-0000-4000-8000-000000000103",
                "00000000-0000-4000-8000-000000000104",
            ),
            selected,
            route_task(
                app,
                guided_route,
                guided_task,
                "00000000-0000-4000-8000-000000000107",
                linkage(selected),
            ),
            route_task(app, store.route, failed_task, failed_request),
            route_task(app, retry, failed_task, "00000000-0000-4000-8000-000000000108"),
            # The guided discovery sent again: the stored result comes back.
            discover(app, guided, "00000000-0000-4000-8000-000000000106"),
        ]
    found, linked, plain, selected, guided_linked, again, retried, repeated = later["before"]
    assert repeated == selected
    assert found["status"] == "no_optional_guidance"
    assert selected["status"] == "selected_guidance" and selected["details"]["guidance_refs"]
    assert guided_linked["details"]["discovery_ref"] == linkage(selected)
    assert again == failed
    assert (
        retried["execution_plan"]["predecessor_plan_id"]
        == failed["execution_plan"]["execution_plan_id"]
    )
    for decision in (linked, plain, guided_linked, retried):
        assert decision["status"] == "ready", decision.get("error_code")
        assert decision["details"]["versions"]["policy_revision"] == "one"
    assert later["after"] == later["before"]


@pytest.mark.parametrize("text", REFUSED, ids=["name-and-sign", "bearer", "pem"])
def test_import_and_restore_write_saved_text_back_unchecked(tmp_path, synthetic, text):
    """SL-3 Delivers, and the plan's gate row for Consiliency/jevdrill#53 (verified as
    built by SL-3's controls): import and restore write saved text back as it was saved,
    unchecked, also with raw retention off (sanitization contract, line 30).

    The analysis that returns the imported text unchecked rests on contract line 31: text
    read back from the local stores is not checked again.
    """
    with pytest.raises(ContractError):
        redact(text)
    _, route, scope = inputs()
    source = application(tmp_path / "source" / "route.db", scope, synthetic)
    task = str(uuid4())
    decision = route_task(source, route, task, str(uuid4()))
    event = {
        "schema_version": "1",
        "event_id": str(uuid4()),
        "task_id": task,
        "routing_decision_id": decision["details"]["routing_decision_id"],
        "execution_run_id": str(uuid4()),
        "source_id": "synthetic-host",
        "source_sequence": 1,
        "occurred_at": "2026-10-09T00:00:00Z",
        "supersedes_event_id": None,
        "payload": {
            "kind": "lifecycle",
            "event_type": "failed",
            "applied_plan_id": None,
            "reason": text,
        },
    }
    envelope = dict(route["request"]["envelope"], operation="report", request_id=str(uuid4()))
    # A new submission of the text is refused, before anything is stored: as a task, as
    # recorded context, as a report (contract lines 7 and 16).
    with pytest.raises(ContractError):
        route_task(source, route, str(uuid4()), str(uuid4()), retain_raw=True, text=text)
    with pytest.raises(ContractError):
        source.analyze(analysis(scope, "record", context_for(decision, task_group=text)))
    with pytest.raises(ContractError):
        source.report({"envelope": envelope, "event": event})
    # The store holds it as saved before today's check: as raw task text, as raw output,
    # as recorded context and as a report.
    # Distinct bytes for each raw kind, each refused today.
    saved = {"raw_task": text.encode(), "raw_output": (text + "\nsynthetic output").encode()}
    for content in saved.values():
        with pytest.raises(ContractError):
            redact(content.decode())
    identities = {kind: stage(source, scope, task, saved[kind], kind) for kind in RAW}
    source.storage.record_learning_context(scope, context_for(decision, task_group=text))
    assert (
        source.storage.ingest_report(
            dict(scope, operation="report"), event["event_id"], canonical_digest(event), event
        )["status"]
        == "accepted"
    )

    key = Fernet.generate_key()
    bundle = source.recover(recovery(scope, "backup", key))["encrypted_bundle"]
    fresh = application(tmp_path / "fresh" / "route.db", scope, synthetic)
    off = str(uuid4())
    assert route_task(fresh, route, off, str(uuid4()), retain_raw=False)["status"] == "ready"
    assert active_bytes(fresh, scope, off, "raw_task") == []
    imported = fresh.recover(recovery(scope, "import", key, bundle))
    assert imported["status"] == "imported" and imported["restored_count"] == len(RAW)
    for kind in RAW:
        assert active_bytes(fresh, scope, task, kind) == [saved[kind]]
    groups = fresh.analyze(analysis(scope))["groups"]
    assert [g["conditions"]["task_group"] for g in groups] == [text]
    events = fresh.storage.project_run(scope, event["execution_run_id"])["events"]
    assert [e["payload"]["reason"] for e in events] == [text]

    archives = archive_item(source, scope, synthetic, *(identities[kind] for kind in RAW))
    for kind in RAW:
        assert active_bytes(source, scope, task, kind) == []
    assert route_task(source, route, str(uuid4()), str(uuid4()), retain_raw=False)["status"] == (
        "ready"
    )
    for kind, (archived, _) in zip(RAW, archives, strict=True):
        restored = source.recover(recovery(scope, "restore", artifact=archived))
        assert restored["status"] == "restored" and restored["restored_count"] == 1
        assert active_bytes(source, scope, task, kind) == [saved[kind]]


def test_completed_maintenance_whose_follow_up_refuses_stored_objectives_answers_invalid_input(
    tmp_path, synthetic, monkeypatch
):
    """SL-3 Delivers, and the plan's gate row for Consiliency/jevdrill#58 (verified as
    built by SL-3's controls); sanitization contract, line 31: the run's maintenance work
    is committed, and the command answers `invalid_input`.

    Through `Application` the answer is a `ContractError`, a `ValueError` whose message
    does not contain "conflict": the command line prints `invalid_input` for exactly that
    (`cli.py:199-203`, `:211-213`).
    """
    _, route, scope = inputs()
    app = application(tmp_path / "route.db", scope, synthetic)
    decision = route_task(app, route, str(uuid4()), str(uuid4()))
    record(app, scope, decision)
    objective = dict(route["request"]["optimization_objective"], objective_id=REFUSED[0])
    with pytest.raises(ContractError):
        app.analyze(analysis(scope, objectives=[objective]))
    # Stored before the check refused it, as after an upgrade that changes the check.
    with monkeypatch.context() as earlier:
        earlier.setattr("jevdrill.application.redact", lambda text, deadline=None: text)
        assert app.analyze(analysis(scope, objectives=[objective]))["status"] == "updated"
    task = decision["details"]["task_id"]
    identity = stage(app, scope, task, b"synthetic task")
    directory = app.storage._artifact_directory(app.storage._task_scope(scope))

    synthetic.now = START + 30 * DAY
    with pytest.raises(ContractError, match="credential-like material") as answer:
        app.maintain(maintenance(scope))
    assert isinstance(answer.value, ValueError) and "conflict" not in str(answer.value)
    notices = app.notices({"schema_version": "1", "scope": scope})["notices"]
    assert [n["kind"] for n in notices] == ["archive_prompt"]

    synthetic.now += 7 * DAY
    with pytest.raises(ContractError, match="credential-like material"):
        app.maintain(maintenance(scope))
    assert not (directory / identity).exists()
    assert app.notices({"schema_version": "1", "scope": scope})["notices"] == []
    with app.storage._connect() as c:
        assert c.execute(
            "SELECT 1 FROM artifact_lifecycle WHERE source_id=? AND archived=?",
            (identity, synthetic.now),
        ).fetchone()

    # A completed run with nothing to process answers the same way: invalid_input.
    synthetic.now += 1
    with pytest.raises(ContractError, match="credential-like material") as answer:
        app.maintain(maintenance(scope))
    assert isinstance(answer.value, ValueError) and "conflict" not in str(answer.value)


def test_deleted_supporting_data_restores_no_earlier_verified_policy(tmp_path, synthetic):
    """EC-LEARN-3 "Policy validation becomes stale without automatic rollback" (D new,
    SL-3): with an earlier verified policy, none restored.

    The later policy shares no supporting task with the earlier one, so the earlier one
    stays verified and current whichever task goes. Each of the later policy's 200
    supporting tasks (100 holdout cases, then 100 regression cases, the last one recorded
    included) is deleted in turn, each in its own copy of the store.
    """
    _, route, scope = inputs()
    template = tmp_path / "template"
    app = application(template / "route.db", scope, synthetic, policy=True)
    tasks = [str(uuid4()) for _ in range(400)]
    for task in tasks:
        seed_task(app.storage, scope, task)
    first = promote(app, scope, definition("one", "execution-ceilings-v1", route, tasks[:200]))
    second = promote(app, scope, definition("two", "one", route, tasks[200:]))
    earlier = inspect_policy(app, first)
    assert earlier["policy_status"] == "evaluated" and earlier["reasons"] == []
    later = inspect_policy(app, second)
    assert later["previous_policy_revision"] == "one"
    supporting = [case["task_id"] for case in later["definition"]["cases"]]
    assert supporting == tasks[200:]
    routed = route_task(app, route, str(uuid4()), str(uuid4()))
    assert routed["status"] == "ready"
    assert routed["details"]["versions"]["policy_revision"] == "two"

    for position, task in enumerate(supporting):
        copied = tmp_path / "deleted"
        shutil.copytree(template, copied)
        store = application(copied / "route.db", scope, synthetic, policy=True)
        assert store.delete_task(scope, task)["status"] == "deleted"
        stale = inspect_policy(store, second)
        assert stale["policy_status"] == "stale", position
        assert stale["reasons"] == ["supporting_data_deleted"], position
        for _ in range(2):
            routed = route_task(store, route, str(uuid4()), str(uuid4()))
            assert routed["status"] == "routing_failed", position
            assert routed["error_code"] == "policy_verification_required", position
        assert inspect_policy(store, first) == earlier, position
        shutil.rmtree(copied)


@pytest.mark.parametrize("content", [AWKWARD, TEXT, BOM], ids=["invalid-utf8", "utf8", "utf8-bom"])
@pytest.mark.parametrize("kind", ["raw_task", "raw_output", "context"])
def test_restored_bytes_equal_the_original(tmp_path, synthetic, kind, content):
    """EC-LEARN-3 "Restoration" (D new, SL-3): restored bytes equal the original, for
    bytes that are not text, for valid UTF-8 text and for that text after a byte-order
    mark, each with every line ending."""
    _, route, scope = inputs()
    app = application(tmp_path / "route.db", scope, synthetic)
    task = str(uuid4())
    route_task(app, route, task, str(uuid4()))
    identity = stage(app, scope, task, content, kind)
    assert active_bytes(app, scope, task, kind) == [content]
    archived, _ = archive_item(app, scope, synthetic, identity)
    assert active_bytes(app, scope, task, kind) == []
    restored = app.recover(recovery(scope, "restore", artifact=archived))
    assert restored["restored_count"] == 1
    assert active_bytes(app, scope, task, kind) == [content]


def analysed(app, scope):
    return {s["task_id"] for g in app.analyze(analysis(scope))["groups"] for s in g["sources"]}


@pytest.mark.parametrize("order", ["deletions_first", "deletions_last", "tombstones_only"])
def test_backup_deletion_records_are_honoured_in_a_fresh_store(tmp_path, synthetic, order):
    """EC-LEARN-3 "Deletion records applied before restored or imported analysis" (D new,
    SL-3): a backup's own deletion records honoured in a fresh store.

    `tombstones_only` deletes every task and the objective, so the later backup holds
    deletion records and nothing live; it is imported before the earlier backup.
    """
    discovery, route, scope = inputs()
    source = application(tmp_path / "source" / "route.db", scope, synthetic)
    link = linkage(discover(source, discovery, str(uuid4())))
    linked = route_task(source, route, str(uuid4()), str(uuid4()), link)
    record(source, scope, linked, link)
    deleted = route_task(source, route, str(uuid4()), str(uuid4()))
    record(source, scope, deleted)
    kept = route_task(source, route, str(uuid4()), str(uuid4()))
    record(source, scope, kept)
    tasks = {d["details"]["task_id"]: d for d in (linked, deleted, kept)}
    key = Fernet.generate_key()
    earlier = source.recover(recovery(scope, "backup", key))["encrypted_bundle"]
    removed = [deleted, linked, kept] if order == "tombstones_only" else [deleted]
    source.delete_discovery(dict(scope, operation="discover"), link["work_objective_id"])
    for decision in removed:
        source.delete_task(scope, decision["details"]["task_id"])
    later = source.recover(recovery(scope, "backup", key))["encrypted_bundle"]
    body = json.loads(decrypt_archive(later.encode(), key))
    assert body["objectives"] == {link["work_objective_id"]: True}
    for decision in removed:
        assert body["tasks"][decision["details"]["task_id"]] is True
    if order == "tombstones_only":
        assert all(body["tasks"].values()) and set(body["tasks"]) == set(tasks)
        assert [body[k] for k in ("decisions", "events", "contexts", "artifacts")] == [[]] * 4
        # Imported alone, the earlier backup makes every task analysable again.
        alone = application(tmp_path / "alone" / "route.db", scope, synthetic)
        assert alone.recover(recovery(scope, "import", key, earlier))["status"] == "imported"
        assert analysed(alone, scope) == set(tasks)
    else:
        # The later backup still holds the linked task's decision and context.
        assert linked["details"]["task_id"] in {c["task_id"] for c in body["contexts"]}

    fresh = application(tmp_path / "fresh" / "route.db", scope, synthetic)
    for bundle in [earlier, later] if order == "deletions_last" else [later, earlier]:
        assert fresh.recover(recovery(scope, "import", key, bundle))["status"] == "imported"
        if bundle is later:
            # Straight after this import, the destination holds the objective's tombstone.
            held = fresh.recover(recovery(scope, "backup", key))["encrypted_bundle"]
            objectives = json.loads(decrypt_archive(held.encode(), key))["objectives"]
            assert objectives == {link["work_objective_id"]: True}
    expected = set() if order == "tombstones_only" else {kept["details"]["task_id"]}
    assert analysed(fresh, scope) == expected
    for decision in removed:
        assert fresh.replay(scope, decision["details"]["routing_decision_id"]) is None
