"""HOST SL-5: no dry run becomes a learning observation (Consiliency/jevdrill#109).

Each observation case routes a dry run and, beside it, a main and a delegated real
run, gives all three the same reports, and checks the observations in the deciding store and in a fresh store after an
export and an import. Inputs are the committed synthetic route fixture; a judgment
port that fails if called is injected, so no request leaves the runner.
"""

import json
import sqlite3
import time
from pathlib import Path
from uuid import uuid4

import pytest

from jevdrill import routing, storage
from jevdrill.application import Application
from jevdrill.contracts import canonical_digest, parse_contract
from jevdrill.storage import SQLiteStorage

LIFECYCLE = (
    "queued",
    "started",
    "plan_applied",
    "completed",
    "failed",
    "canceled",
    "guidance_deactivated",
)
REPORTS = [f"lifecycle:{name}" for name in LIFECYCLE] + ["usage", "evaluation", "host_choice"]
CASES = [*REPORTS, "none"]  # 11 report sets: every kind and every event_type, and none


class ForbiddenJudge:
    """Stand-in judgment port that fails the test if it is called at all."""

    model_revision = "jev-latest"

    def judge(self, *args):
        raise AssertionError("judgment port called")


def route(app, mode, task=None):
    value = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-application.json").read_text()
    )[0]["payload"]
    value["request"].update(task_id=task or str(uuid4()), execution_mode=mode, active_guidance=[])
    value["request"]["envelope"].update(request_id=str(uuid4()), idempotency_key=str(uuid4()))
    value["settings_layers"] = [{"source": "request", "values": {"local_analysis_enabled": True}}]
    value["inventory"]["candidates"][0]["guidance_options"] = []
    result = app.route(value)
    assert result["status"] == "ready"
    envelope = value["request"]["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "route",
    }
    context = {
        "task_id": value["request"]["task_id"],
        "routing_decision_id": result["details"]["routing_decision_id"],
        "discovery_ref": None,
        "task_family": "implementation",
        "task_group": "parser",
        "environment_revision": "native-v1",
        "isolation_revision": "temp-v1",
        "evaluator_ref": "checks-v1",
        "rubric_revision": "v1",
        "local_analysis_enabled": True,
        "share_user_wide": False,
    }
    app.storage.deadline = None
    app.storage.record_learning_context(scope, context)
    return scope, context, result


def payload(case, decision, run):
    kind, _, name = case.partition(":")
    if kind == "lifecycle":
        applied = (
            decision["execution_plan"]["execution_plan_id"] if name == "plan_applied" else None
        )
        return {"kind": "lifecycle", "event_type": name, "applied_plan_id": applied, "reason": None}
    if kind == "usage":
        value = {"kind": "known", "value": 12, "unit": "tokens"}
        return {
            "kind": "usage",
            "measurements": [
                {
                    "metric_id": "input_tokens",
                    "metric_version": "v1",
                    "measurement_value": value,
                    "source": "host",
                    "method": "direct-v1",
                    "scope": "run",
                    "counting_semantics": "disjoint",
                    "parent_metric_id": None,
                }
            ],
        }
    if kind == "evaluation":
        required = decision["details"]["optimization_objective"]["acceptance_requirements"]
        checks = {row["requirement_id"]: True for row in required} or {"tests": True}
        return {
            "kind": "evaluation",
            "evaluator_ref": "checks-v1",
            "rubric_revision": "v1",
            "check_results": checks,
            "measurements": [],
        }
    return {"kind": "host_choice", "selected_run_id": run, "reason": "synthetic preference"}


def report(store, scope, context, decision, case):
    """Send the case's reports for one run; `completed` follows `plan_applied`, as in #109."""
    run = str(uuid4())
    cases = ["lifecycle:plan_applied", case] if case == "lifecycle:completed" else [case]
    for sequence, name in enumerate(cases, 1):
        event = {
            "schema_version": "1",
            "event_id": str(uuid4()),
            "task_id": context["task_id"],
            "routing_decision_id": context["routing_decision_id"],
            "execution_run_id": run,
            "source_id": "synthetic-host",
            "source_sequence": sequence,
            "occurred_at": "2026-11-22T00:00:00Z",
            "supersedes_event_id": None,
            "payload": payload(name, decision, run),
        }
        parse_contract("ExecutionEvent", event)
        result = store.ingest_report(
            dict(scope, operation="report"), event["event_id"], canonical_digest(event), event
        )
        assert result["status"] == "accepted" and result["durable"] is True
    return run


def observed(store, scope, decision_id):
    rows = store.learning_observations(scope)
    return [r for r in rows if r["source"]["routing_decision_id"] == decision_id]


def test_routing_and_storage_share_the_dry_run_code():
    assert routing.DRY_RUN_DIAGNOSTIC == storage.DRY_RUN_DIAGNOSTIC == "dry_run_decision"


@pytest.mark.parametrize("where", ["deciding", "imported"])
@pytest.mark.parametrize("case", CASES)
def test_no_dry_run_becomes_an_observation(tmp_path, case, where):
    app = Application(SQLiteStorage(tmp_path / "route.db"), judgments=ForbiddenJudge())
    scope, dry_context, dry = route(app, "dry_run")
    decisions = [(dry_context, dry)]
    decisions += [route(app, mode)[1:] for mode in ("main", "delegated")]
    runs = {}
    for context, decision in decisions:
        if case != "none":
            runs[context["routing_decision_id"]] = report(
                app.storage, scope, context, decision, case
            )
    ids = {context["routing_decision_id"] for context, _ in decisions}
    store = app.storage
    if where == "imported":
        body = store.export_recovery(scope)
        store = SQLiteStorage(tmp_path / "fresh.db")
        store.import_recovery(scope, body, time.time())
        arrived = store.export_recovery(scope)
        assert ids <= {d["bundle"]["routing_decision_id"] for d in arrived["decisions"]}
        assert ids <= {c["routing_decision_id"] for c in arrived["contexts"]}
        events = sorted(json.dumps(e, sort_keys=True) for e in body["events"])
        assert sorted(json.dumps(e, sort_keys=True) for e in arrived["events"]) == events
    assert observed(store, scope, dry_context["routing_decision_id"]) == []
    for context, _ in decisions[1:]:  # the main and the delegated real runs
        (row,) = observed(store, scope, context["routing_decision_id"])
        if case != "none":
            assert row["source"]["execution_run_id"] == runs[context["routing_decision_id"]]
        if case == "lifecycle:completed":
            assert row["status"] == "completed"


def edit_diagnostics(path, identity, diagnostics):
    """Rewrite one stored decision's diagnostics, standing in for another store's record."""
    with sqlite3.connect(path) as connection:
        (raw,) = connection.execute(
            "SELECT bundle FROM decisions_v1 WHERE decision_id=?", (identity,)
        ).fetchone()
        bundle = json.loads(raw)
        bundle["decision"]["details"]["diagnostics"] = diagnostics
        connection.execute(
            "UPDATE decisions_v1 SET bundle=? WHERE decision_id=?",
            (json.dumps(bundle, sort_keys=True, separators=(",", ":")), identity),
        )


@pytest.mark.parametrize("matching", [True, False], ids=["matching", "mismatching"])
@pytest.mark.parametrize("mode", ["dry_run", "main"])
def test_cached_decision_is_reused_only_when_its_mode_matches(tmp_path, mode, matching):
    app = Application(SQLiteStorage(tmp_path / "route.db"), judgments=ForbiddenJudge())
    _, _, first = route(app, mode)
    identity = first["details"]["routing_decision_id"]
    marker = {
        "code": "dry_run_decision",
        "summary": "Decision for a dry run; excluded from learning observations.",
        "evidence_refs": [],
        "resolution_advice": [],
    }
    if not matching:
        # A dry-run decision recorded before the fix (marker removed), or a real decision
        # given the marker by an altered import.
        edit_diagnostics(app.storage.path, identity, [] if mode == "dry_run" else [marker])
    _, _, second = route(app, mode, task=first["details"]["task_id"])
    assert second["details"]["reused_decision_id"] == (identity if matching else None)
    codes = [row["code"] for row in second["details"]["diagnostics"]]
    assert codes == (["dry_run_decision"] if mode == "dry_run" else [])
